# 跑去邮箱把信拿回来,列编号，盖章

import asyncio
from email import message_from_bytes
from email.message import Message
import imaplib
from typing import Optional

from loguru import logger

# def do_thing():
#     """收件"""
# 因为 imap依赖的python包 imaplib是同步库，如果不用下面这个方法的话，会把整个程序卡住
# asyncio.to_thread(do_thing) , 把这件事情交给另一个线程去做，这样我还可以去干别的事情


class ImapMail:
    # ============== 连接类 =====================
    def __init__(self, host, port=993, *, ssl=True):

        self._host = host
        self._port = port
        self._ssl = ssl
        self._conn = None  # 连接对象
        self._username = None
        self._password = None
        self._mailbox = None

    async def connect(self):
        """连接服务器"""

        def _connect():
            if self._ssl:
                return imaplib.IMAP4_SSL(self._host, self._port)  # 加密连接
            return imaplib.IMAP4(self._host, self._port)  # 普通连接

        self._conn = await asyncio.to_thread(_connect)  # 连接对象

    def ImapConn(self):
        if not self._conn:
            raise RuntimeError("IMAP暂未连接")

    async def login(self, username, password):
        """登录"""
        # if not self._conn:
        #     raise RuntimeError("IMAP暂未连接")
        self.ImapConn()
        # 这个连接对象就有.login 这个方法，就是告诉这个连接对象我的账号和密码，去登录！
        await asyncio.to_thread(self._conn.login, username, password)
        self._username = username
        self._password = password

    async def select(self, mailbox="INBOX"):
        """要看邮箱里面的哪个文件夹"""
        # if not self._conn:
        #     raise RuntimeError("IMAP暂未连接")
        self.ImapConn()
        await asyncio.to_thread(self._conn.select, mailbox)
        self._mailbox = mailbox

    async def logout(self):
        """断开"""
        if not self._conn:
            return  # 没连就不用断开
        try:
            await asyncio.to_thread(self._conn.logout)
        finally:
            self._conn = None  # 不论成功失败，都要把连接置空

    async def _reconnect(self):
        """重新连接并恢复登录状态（如果之前已登录）。"""
        # 1.关旧连接
        if self._conn:
            try:
                await asyncio.to_thread(self._conn.logout)
            except Exception as e:
                return f"关闭旧连接失败，错误{e}"
            finally:
                self._conn = None

        # 2.重连
        await self._connect()

        # 3. 恢复登录状态
        if self._username and self._password:
            await self.login(self._username, self._password)
            if self._mailbox:
                self.select(self._mailbox)

    # ============== 搜索类 =====================
    async def search_uids(self, criteria: str) -> list[str]:
        """取信前，先搜一下编号 返回UID列表"""
        # if not self._conn:
        #     raise RuntimeError("IMAP暂未连接")
        self.ImapConn()

        def _search():
            # SEARCH 表搜索命令 ， None:是给搜索命令的额外参数（这里不用） ，criteria：搜索条件比如all
            # imaplib的原始调用 (typ, data)：typ 是 "OK" 表示成功，data 是结果。
            typ, data = self._conn.uid("SEARCH", None, criteria)  # 找编号
            if typ != "OK":
                raise RuntimeError(f"IMAP搜索失败 {typ}{data}")
            raw = data[0] or b""
            return [
                x.decode() if isinstance(x, bytes) else str(x) for x in raw.split() if x
            ]

        try:
            return await asyncio.to_thread(_search)
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.warning(
                "IMAP 连接断了，重连重试... criteria=%s, error=%s", criteria, e
            )
            await self._reconnect()
            return await asyncio.to_thread(_search)

    # ============== 取信类 =====================
    async def fetch_rfc822(self, uid: str) -> Message:
        self.ImapConn()

        def _fetch():
            # FETCH 取信 ； uid 要取哪一份， "(RFC822)" = 取信的完整原始内容（RFC822 是邮件格式标准，意思是"整封信，含所有头、正文、附件"）。
            typ, data = self._conn.uid("FETCH", uid, "(RFC822)")
            if typ != "OK":
                raise RuntimeError(f"IMAP FETCH failed: {typ} {data}")
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    # 把"原始字节"转成 Python 的 Message 对象（email 模块的标准对象）。
                    return message_from_bytes(item[1])  # 关键转换
            raise RuntimeError("IMAP FETCH returned no message")

        try:
            return await asyncio.to_thread(_fetch)
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.warning("IMAP 连接断了，重连重试... uid=%s, error=%s", uid, e)
            await self._reconnect()
            return await asyncio.to_thread(_fetch)

    async def fetch_many_rfc822(self, uids) -> list[tuple[str, Message]]:
        """取多封"""
        out = []
        for uid in uids:
            try:
                msg = await self.fetch_rfc822(uid)
                out.append((str(uid), msg))
            except Exception as e:
                logger.exception("fetch message failed uid=%s: %s", uid, e)
        return out

    async def get_latest_uids(self, limit=10, *, criteria="ALL") -> list[str]:
        """拿最新的N封信件
        信越晚到，uid越大
        """
        uids = await self.search_uids(criteria)
        return uids[-limit:]

    async def get_max_uid(self) -> Optional[int]:
        """拿到当前最大的UID"""
        uids = await self.search_uids("ALL")
        if not uids:
            return None
        try:
            return max(int(x) for x in uids)
        except ValueError:
            return None

    # ============== 标记类 =====================
    async def mark_seen(self, uid: str) -> None:
        """把一封信标记为已读"""
        self.ImapConn()

        def _store():
            # STORE 修改信件的标志； uid哪一封； +FLAGS：添加一个标志（ + 是添加，-是移除） r"(\\Seen)" 要添加的标志是 \Seen（已读）
            typ, data = self._conn.uid("STORE", uid, "+FLAGS", r"(\\Seen)")  # 关键调用
            if typ != "OK":
                raise RuntimeError(f"IMAP STORE \\Seen failed: {typ} {data}")

        try:
            await asyncio.to_thread(_store)
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.warning("IMAP 连接断了，重连重试... uid=%s, error=%s", uid, e)
            await self._reconnect()
            await asyncio.to_thread(_store)

    async def mark_many_seen(self, uids) -> None:
        """批量标记已读"""
        uid_list = [str(u) for u in uids]
        if not uid_list:
            return
        self.ImapConn()

        uid_set = ",".join(uid_list)  # 把 ["100","101"] 拼成 "100,101"

        def _store_many():
            typ, data = self._conn.uid("STORE", uid_set, "+FLAGS", r"(\\Seen)")
            if typ != "OK":
                raise RuntimeError(f"IMAP STORE \\Seen (many) failed: {typ} {data}")

        try:
            await asyncio.to_thread(_store_many)
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.warning("...uids=%s...", uid_set, e)
            await self._reconnect()
            await asyncio.to_thread(_store_many)
