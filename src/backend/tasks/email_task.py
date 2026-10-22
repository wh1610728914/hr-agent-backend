from smtplib import SMTPResponseException
from loguru import logger
from backend.core.mail import create_mail_instance
from fastapi_mail import FastMail, MessageSchema


async def send_email_task(message: MessageSchema):
    """发送邮件"""
    mail: FastMail = create_mail_instance()
    try:
        await mail.send_message(message)
    except SMTPResponseException as e:
        if e.code == -1 and b"\x00\x00\x00" in str(e).encode():
            logger.info(
                "⚠️ 忽略 QQ 邮箱 SMTP 关闭阶段的非标准响应（邮件已成功发送）",
                enqueue=True,
            )
        else:
            logger.error(f"邮件发送失败！{e}")


async def send_invite_email_task(email: str, invite_code: str):
    """给指定邮箱发送验证码"""
    message = MessageSchema(
        recipients=[email],
        subject="【您的系统名称】注册验证码",
        body=f"您好！\n\n您的验证码是：{invite_code}，有效期 15天。请勿泄露给他人。",
        subtype="plain",
    )
    await send_email_task(message)
