# 装邮件的容器

from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from typing import Optional


# frozen=True不允许修改
@dataclass(frozen=True)
class EmailAddress:
    name: str
    address: str


@dataclass(frozen=True)
class ParsedEmail:
    uid: str  # 邮件编号（唯一标识）
    message_id: str  # 邮件的 Message-ID（回信时用来标记"我在回哪封"）
    subject: str  # 主题
    from_: EmailAddress  # 发件人（为什么叫 from_ 带下划线？因为 from 是 Python 关键字，不能直接用）
    to: list[EmailAddress]  # 收件人（可能多个，所以是列表）
    cc: list[EmailAddress]  # 抄送（可能多个）
    date: Optional[datetime]  # 日期，可能解析失败所以是 Optional（可为 None）
    text: str  # 纯文本正文
    html: str  # HTML 正文
    raw: Message  # 原始邮件对象（保留原样，回信时还要从里面取 Reply-To 等）
