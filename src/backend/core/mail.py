# 使用fastapi-mail库初始化邮件发送实例的代码

from backend import settings
from fastapi_mail import ConnectionConfig, FastMail
from pydantic import SecretStr


def create_mail_instance():
    """创建fastMail实例（每次调用返回新实例）"""
    mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,  # 发件账号
        MAIL_PASSWORD=SecretStr(
            settings.MAIL_PASSWORD
        ),  # 密码（包装成 SecretStr 防泄漏）
        MAIL_FROM=settings.MAIL_FROM,  # 发件人邮箱
        MAIL_PORT=settings.MAIL_PORT,  # 端口（587）
        MAIL_SERVER=settings.MAIL_SERVER,  # 服务器（smtp.qq.com）
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,  # 发件人昵称（知了课堂）
        MAIL_STARTTLS=settings.MAIL_STARTTLS,  # 启用 STARTTLS
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,  # 关闭 SSL/TLS
        USE_CREDENTIALS=True,  # 是否使用账号密码认证（当然要 True）
        VALIDATE_CERTS=True,  # 是否验证服务器的 SSL 证书（生产环境必须 True，防止中间人攻击）
    )
    return FastMail(mail_config)
