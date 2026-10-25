# 把收信，发信，解析 组装


from email.message import EmailMessage
from email.utils import make_msgid
import smtplib

from backend.emailBot.imap_client import ImapMail
from backend.emailBot.models import ParsedEmail
from backend.emailBot.parser import parse_email
from backend.emailBot.settings import EmailBotSetting
from loguru import logger


class EmailBot:

    def __init__(self, settings: EmailBotSetting):
        self.settings = settings
        self._imap = ImapMail(
            host=settings.imap_host, port=settings.imap_port, ssl=settings.imap_ssl
        )
        self._smtp = ImapMail(
            host=settings.smtp_host,
            port=settings.smtp_port,
            starttls=settings.smtp_starttls,
        )
        self.is_connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        """连接"""
        await self._imap.connect()
        await self._imap.login(self.settings.email, self.settings.password)
        await self._imap.select(self.settings.imap_mailbox)

        await self._smtp.connect()
        await self._smtp.login(self.settings.email, self.settings.password)

        self.is_connected = True

    async def close(self):
        """关闭"""

        await self._imap.logout()
        await self._smtp.quit()
        self.is_connected = False

    async def _ensure_connected(self):
        """懒加载，没连就先连"""
        if not self.is_connected:
            await self.connect()

    async def fetch_latest(self, criteria="ALL"):
        """拿最新的N封"""
        await self._ensure_connected()
        limit = limit or self.settings.default_fetch_limit
        uids = await self._imap.get_latest_uids(limit=limit, criteria=criteria)
        pairs = await self._imap.fetch_many_rfc822(uids)
        return [parse_email(uid, msg) for uid, msg in pairs]

    async def fetch_since_uid(
        self, last_uid: int, *, criteria="ALL"
    ) -> list[ParsedEmail]:
        """拿 UID 比 last_uid 大的信"""

        await self._ensure_connected()
        # Using UID SEARCH with a range.
        # Example: UID 123:*  (inclusive)
        uids = await self._imap.search_uids(f"UID {last_uid + 1}:*")
        if criteria and criteria not in {"ALL", "(ALL)"}:
            # 如果用户想要 UNSEEN 等条件，就组合
            uids2 = await self._imap.search_uids(
                f"(UID {last_uid + 1}:* {criteria.strip('()')})"
            )
            uids = uids2
        pairs = await self._imap.fetch_many_rfc822(uids)
        return [parse_email(uid, msg) for uid, msg in pairs]

    async def get_max_uid(self):
        """拿当前最大 UID"""

        await self._ensure_connected()
        return await self._imap.get_max_uid()

    async def send_email(self, *, to, subject, text, html=None, cc=None) -> None:
        """凭空捏造一封信"""
        await self._ensure_connected()
        # 造一封信
        msg = EmailMessage()
        msg["From"] = self.settings.email
        msg["To"] = ", ".join(to) if isinstance(to, list) else to
        if cc:
            msg["Cc"] = ", ".join(cc) if isinstance(cc, list) else cc
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid()

        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        try:
            # 发出去
            await self._smtp.send_message(msg)
        except smtplib.SMTPServerDisconnected:
            logger.warning("SMTP disconnected. Reconnecting and retrying...")
            await self._reconnect_smtp()
            await self._smtp.send_message(msg)  # Retry once

    async def _reconnect_smtp(self):
        """发信错误 后重连"""
        logger.info("Reconnecting SMTP client...")
        await self._smtp.quit()  # 优雅关闭旧连接（可能已经死了，quit 会报错）
        await self._smtp.connect()  # 重新连
        await self._smtp.login(self.settings.email, self.settings.password)  # 重新登录

    async def reply(self, email: ParsedEmail, *, text, subject_prefix="Re: "):
        """回复某信"""
        # 确定收件人
        raw = email.raw  # raw 原始邮件对象
        reply_to = (raw.get("Reply-To") or "").strip() or email.from_.address
        if not reply_to:
            raise ValueError("Cannot reply: missing sender address")
        # 确定主题
        subject = email.subject
        if subject_prefix and not subject.lower().startswith(
            subject_prefix.strip().lower()
        ):
            subject = f"{subject_prefix}{subject}"

        # 构造信
        msg = EmailMessage()
        msg["From"] = self.settings.email
        msg["To"] = reply_to
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid()

        # 设置线程头
        if email.message_id:
            msg["In-Reply-To"] = email.message_id
            refs = (raw.get("References") or "").strip()
            msg["References"] = (  # References 整条对话链
                (refs + " " + email.message_id).strip() if refs else email.message_id
            )

        msg.set_content(text)

        try:
            await self._smtp.send_message(msg)
        except smtplib.SMTPServerDisconnected:
            logger.warning("SMTP disconnected. Reconnecting and retrying reply...")
            await self._reconnect_smtp()
            await self._smtp.send_message(msg)

        logger.info(
            "Replied to uid={} from={} subject={}",
            email.uid,
            email.from_.address,
            email.subject,
        )

        # 异步标为已读，回复完信后，就把这封信标为已读
        try:
            import asyncio

            if email.uid is not None:
                asyncio.create_task(self._imap.mark_seen(str(email.uid)))
        except Exception as e:
            logger.exception("schedule mark_seen failed uid=%s: %s", email.uid, e)
