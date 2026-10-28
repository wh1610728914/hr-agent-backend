from __future__ import annotations

from email.message import EmailMessage
from email.utils import make_msgid
import smtplib

from .imap_client import ImapMail
from .smtp_client import SmtpMail
from .parser import parse_email
from .models import ParsedEmail
from .settings import EmailBotSetting
from loguru import logger


class EmailBot:
    """High-level facade: read/parse/reply/send.

    Typical usage:
        settings = Settings()
        bot = EmailBot(settings)
        async with bot:
            emails = await bot.fetch_latest(limit=10)
    """

    def __init__(self, settings: EmailBotSetting):
        """初始化 EmailBot。

        根据配置创建 IMAP 与 SMTP 客户端实例，并初始化连接状态标记。

        Args:
            settings: 邮件机器人配置对象，包含 IMAP/SMTP 主机、端口、
                登录邮箱、密码、邮箱文件夹等配置项。
        """

        self.settings = settings
        self._imap = ImapMail(
            host=settings.imap_host,
            port=settings.imap_port,
            ssl=settings.imap_ssl,
        )
        self._smtp = SmtpMail(
            host=settings.smtp_host,
            port=settings.smtp_port,
            starttls=settings.smtp_starttls,
        )
        self.is_connected = False

    async def __aenter__(self) -> "EmailBot":
        """异步上下文管理器入口。

        进入 `async with` 块时自动建立连接，并返回当前实例。

        Returns:
            已完成连接的 EmailBot 实例。
        """

        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """异步上下文管理器出口。

        退出 `async with` 块时自动关闭 IMAP 与 SMTP 连接，
        无论块内是否发生异常都会执行。

        Args:
            exc_type: 异常类型（若有）。
            exc: 异常实例（若有）。
            tb: 异常回溯对象（若有）。
        """

        await self.close()

    async def connect(self) -> None:
        """建立 IMAP 与 SMTP 连接并完成登录。

        依次连接并登录 IMAP 服务器、选择邮箱文件夹，
        再连接并登录 SMTP 服务器，最后将连接状态置为 True。
        """

        await self._imap.connect()
        await self._imap.login(self.settings.email, self.settings.password)
        await self._imap.select(self.settings.imap_mailbox)

        await self._smtp.connect()
        await self._smtp.login(self.settings.email, self.settings.password)
        self.is_connected = True

    async def close(self) -> None:
        """关闭 IMAP 与 SMTP 连接。

        依次登出 IMAP、退出 SMTP，并将连接状态置为 False。
        """

        await self._imap.logout()
        await self._smtp.quit()
        self.is_connected = False

    async def _ensure_connected(self) -> None:
        """确保当前处于已连接状态。

        若 `is_connected` 为 False，则自动调用 `connect()` 建立连接。
        供内部各操作方法在真正执行前调用。
        """

        if not self.is_connected:
            await self.connect()

    async def fetch_latest(
        self, *, limit: int | None = None, criteria: str = "ALL"
    ) -> list[ParsedEmail]:
        """获取最新的若干封邮件并解析。

        Args:
            limit: 获取数量上限，为 None 时使用配置中的默认值。
            criteria: IMAP 搜索条件，默认 "ALL" 表示全部邮件。

        Returns:
            解析后的邮件对象列表，按 UID 获取顺序排列。
        """

        await self._ensure_connected()
        limit = limit or self.settings.default_fetch_limit
        uids = await self._imap.get_latest_uids(limit=limit, criteria=criteria)
        pairs = await self._imap.fetch_many_rfc822(uids)
        return [parse_email(uid, msg) for uid, msg in pairs]

    async def fetch_since_uid(
        self, last_uid: int, *, criteria: str = "ALL"
    ) -> list[ParsedEmail]:
        """获取指定 UID 之后的所有邮件并解析。

        使用 IMAP `UID SEARCH` 的范围语法（如 `UID 123:*`）查询
        UID 大于 `last_uid` 的邮件；若提供了额外搜索条件，
        则将 UID 范围与条件组合后再次查询。

        Args:
            last_uid: 上次已处理的最大 UID，本次从 `last_uid + 1` 开始获取。
            criteria: 附加的 IMAP 搜索条件，默认 "ALL" 表示无附加过滤。

        Returns:
            解析后的邮件对象列表。
        """

        await self._ensure_connected()
        # Using UID SEARCH with a range.
        # Example: UID 123:*  (inclusive)
        uids = await self._imap.search_uids(f"UID {last_uid + 1}:*")
        if criteria and criteria not in {"ALL", "(ALL)"}:
            # If user wants UNSEEN etc. we can combine. Many servers accept: (UID x:* UNSEEN)
            uids2 = await self._imap.search_uids(
                f"(UID {last_uid + 1}:* {criteria.strip('()')})"
            )
            uids = uids2
        pairs = await self._imap.fetch_many_rfc822(uids)
        return [parse_email(uid, msg) for uid, msg in pairs]

    async def get_max_uid(self) -> int | None:
        """获取当前邮箱中的最大 UID。

        常用于记录已处理的邮件进度，便于后续通过
        `fetch_since_uid` 增量拉取新邮件。

        Returns:
            当前邮箱中的最大 UID；若邮箱为空或无法获取则返回 None。
        """

        await self._ensure_connected()
        return await self._imap.get_max_uid()

    async def send_email(
        self,
        *,
        to: str | list[str],
        subject: str,
        text: str,
        html: str | None = None,
        cc: str | list[str] | None = None,
    ) -> None:
        """发送一封新邮件。

        Args:
            to: 收件人地址，支持单个字符串或字符串列表。
            subject: 邮件主题。
            text: 纯文本正文内容。
            html: 可选的 HTML 正文，提供时会作为 alternative 部分附加。
            cc: 可选的抄送地址，支持单个字符串或字符串列表。

        Raises:
            smtplib 相关异常：在重连重试后仍失败时抛出。
        """

        await self._ensure_connected()
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
            await self._smtp.send_message(msg)
        except smtplib.SMTPServerDisconnected:
            logger.warning("SMTP disconnected. Reconnecting and retrying...")
            await self._reconnect_smtp()
            await self._smtp.send_message(msg)  # Retry once

    async def _reconnect_smtp(self):
        """重新建立 SMTP 连接。

        先尝试优雅退出旧连接，再重新连接并登录 SMTP 服务器，
        用于发送过程中遇到连接断开时的重试恢复。
        """

        logger.info("Reconnecting SMTP client...")
        await self._smtp.quit()  # Gracefully close old connection if possible
        await self._smtp.connect()
        await self._smtp.login(self.settings.email, self.settings.password)

    async def reply(
        self,
        email: ParsedEmail,
        *,
        text: str,
        subject_prefix: str = "Re: ",
    ) -> None:
        """回复一封已解析的邮件。

        - 优先回复 Reply-To 地址，若无则回复 From 地址
        - 设置 In-Reply-To 与 References 头部以保证邮件线程正确
        - 发送后异步将原邮件标记为已读（不阻塞当前流程）

        Args:
            email: 需要回复的已解析邮件对象。
            text: 回复正文内容。
            subject_prefix: 主题前缀，默认 "Re: "，若原主题已包含该前缀则不重复添加。

        Raises:
            ValueError: 当无法确定回复地址（缺少 Reply-To 和 From）时抛出。
            smtplib 相关异常：在重连重试后仍失败时抛出。
        """

        raw = email.raw
        reply_to = (raw.get("Reply-To") or "").strip() or email.from_.address
        if not reply_to:
            raise ValueError("Cannot reply: missing sender address")

        subject = email.subject
        if subject_prefix and not subject.lower().startswith(
            subject_prefix.strip().lower()
        ):
            subject = f"{subject_prefix}{subject}"

        msg = EmailMessage()
        msg["From"] = self.settings.email
        msg["To"] = reply_to
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid()

        if email.message_id:
            msg["In-Reply-To"] = email.message_id
            refs = (raw.get("References") or "").strip()
            msg["References"] = (
                (refs + " " + email.message_id).strip() if refs else email.message_id
            )

        msg.set_content(text)
        try:
            await self._smtp.send_message(msg)
        except smtplib.SMTPServerDisconnected:
            logger.warning("SMTP disconnected. Reconnecting and retrying reply...")
            await self._reconnect_smtp()
            await self._smtp.send_message(msg)  # Retry once

        logger.info(
            "Replied to uid={} from={} subject={}",
            email.uid,
            email.from_.address,
            email.subject,
        )

        # 异步标记为已读，不阻塞当前回复流程
        try:
            import asyncio

            if email.uid is not None:
                asyncio.create_task(self._imap.mark_seen(str(email.uid)))
        except Exception as e:
            logger.exception("schedule mark_seen failed uid=%s: %s", email.uid, e)
