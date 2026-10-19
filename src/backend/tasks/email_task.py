from aiosmtplib import SMTPResponseException
from backend.core.mail import create_mail_instance
from loguru import logger
from fastapi_mail import FastMail, MessageSchema


async def send_email_task(message: MessageSchema):
    """发邮件任务"""
    # 1. 每次调用都创建一个新的实例（线程/协程安全）
    mail: FastMail = create_mail_instance()
    try:
        # 2. 真正执行发送
        await mail.send_message(message)
    except SMTPResponseException as e:
        # 3. 处理 QQ 邮箱的“特色”异常
        if e.code == -1 and b"\x00\x00\x00" in str(e).encode():
            logger.info(
                "...忽略 QQ 邮箱 SMTP 关闭阶段的非标准响应（邮件已成功发送）",
                enqueue=True,
            )
        else:
            logger.error(f"邮件发送失败！{e}")


async def send_invite_email_task(email: str, invite_code: str):
    """发邀请码"""
    message = MessageSchema(
        subject="大真邀您在线注册",
        recipients=[email],
        body=f"您好，您的邮箱是：{email}，验证码是：{invite_code}，两天内有效。",
        subtype="plain",
    )
    await send_email_task(message)
