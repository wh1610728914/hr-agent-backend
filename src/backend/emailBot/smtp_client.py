# 把回信送到邮箱

import asyncio
from email import message_from_bytes
from email.message import EmailMessage, Message
import imaplib
import smtplib
from typing import Optional

from backend.core.exceptions import RuntimeError
from loguru import logger

# def do_thing():
#     """收件"""
# 因为 smtp依赖的python包 smtplib是同步库，如果不用下面这个方法的话，会把整个程序卡住
# asyncio.to_thread(do_thing) , 把这件事情交给另一个线程去做，这样我还可以去干别的事情


# 连接 ---》 登录 ---》 寄邮件 ----》 断开
class SmtpMail:
    # ============== 连接类 =====================
    def __init__(self, host, port=587, *, starttls=True):

        self._host = host
        self._port = port
        self._starttls = starttls
        self._conn: smtplib.SMTP | None = None  # 连接对象

    async def connect(self):
        """连接服务器"""

        def _connect():
            conn = smtplib.SMTP(self._host, self._port, timeout=30)
            conn.ehlo()  # ① 打招呼 必须要先打招呼
            if self._starttls:
                conn.starttls()  # ② 升级成加密连接
                conn.ehlo()  # ③ 升级后再打一次招呼 ， 因为加密了，所以再打一次招呼
            return conn

        self._conn = await asyncio.to_thread(_connect)  # 连接对象

    def ImapConn(self):
        if not self._conn:
            raise RuntimeError("IMAP暂未连接")

    async def login(self, username, password):
        """登录"""
        # if not self._conn:
        #     raise RuntimeError("IMAP暂未连接")
        self.ImapConn(self)
        # 这个连接对象就有.login 这个方法，就是告诉这个连接对象我的账号和密码，去登录！
        await asyncio.to_thread(self._conn.login, username, password)

    async def send_message(self, msg: EmailMessage) -> None:
        """发信"""
        self.ImapConn(self)
        await asyncio.to_thread(self._conn.send_message, msg)

    async def quit(self) -> None:
        """下班断开"""
        if not self._conn:
            return
        try:
            await asyncio.to_thread(self._conn.quit)
        finally:
            self._conn = None
