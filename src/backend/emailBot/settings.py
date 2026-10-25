# 配置

from openai import BaseModel
from pydantic import Field


class EmailBotSetting(BaseModel):
    """邮件配置
    imap_xxx 收邮件的配置
    smtp_xxx 发邮件的配置
    """

    imap_host: str = Field(..., description="收信服务器")
    imap_port: int = Field(993, description="收信端口")
    imap_ssl: bool = Field(True, description="加密协议：是否用SSL加密")
    imap_mailbox: str = Field("INBOX", description="收哪个问价夹，默认收件箱")

    smtp_host: str = Field(..., description="发邮件服务器")
    smtp_port: int = Field(587, description="发信端口")
    smtp_starttls: bool = Field(True, description="是否用STARTTLS加密")

    default_fetch_limit: int = Field(10, description="每次检测最新的多少封邮件")
    email: str = Field(..., description="邮箱账号")
    password: str = Field(..., description="密码")
