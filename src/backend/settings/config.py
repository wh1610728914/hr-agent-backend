# 配置数据库
from datetime import timedelta
from urllib.parse import quote_plus

# anyio异步库，这里只用来拼接，用异步简直太小题大做了
# from anyio import Path
from pathlib import Path
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # DBTABASE_URL: str | None = None
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "agent_hr"
    DB_AGENT_NAME: str = "agent_hr_candidate"
    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRES_DAYS: int = 7

    # redis配置
    REDIS_HOST: str
    REDIS_PORT: int

    # 邀请码相关配置
    INVITE_CODE_EXPIRE: int = 60 * 60 * 12 * 2
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    # validation_alias 去读取MAIL_USERNAME作为MAIL_FROM的值
    MAIL_FROM: str = Field(..., validation_alias="MAIL_USERNAME")
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.qq.com"
    MAIL_FROM_NAME: str = "大真真"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # 钉钉配置
    DING_CLIENT_ID: str
    DING_CLIENT_SECRET: str

    # 公网穿透(前后端域名)
    BACKEND_BASE_URL: str

    # 文件简历上传存储路径
    RESUME_DIR: str = os.path.join(BASE_DIR, "upload")

    # OCR 解析文档的token
    OCR_ACCESS_TOKEN: str

    # 大模型配置
    LLM_URL: str
    LLM_QIAN_MODEL: str
    # LLM_DEEPSEEK_MODEL: str

    @computed_field
    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRES_MINUTES)

    @computed_field
    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(days=self.JWT_REFRESH_TOKEN_EXPIRES_DAYS)

    # 动态拼接计算字段
    @computed_field  # 这一行必须在property上面
    # 让函数看起来像变量来用
    @property
    def DATABASE_URL(self) -> str:
        """类型注解 -> str 必须存在，不能省略"""
        # 若密码是p@ssword，直接拼接会变成 ...://user:p@ssword@host...
        # SQLAlchemy 解析会出错。在拼接时加一层转义
        escaped_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg://{self.DB_USER}:{escaped_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # 动态拼接计算字段
    @computed_field  # 这一行必须在property上面
    # 让函数看起来像变量来用
    @property
    def DATABASE_AGENT_URL(self) -> str:
        """类型注解 -> str 必须存在，不能省略"""
        # 若密码是p@ssword，直接拼接会变成 ...://user:p@ssword@host...
        # SQLAlchemy 解析会出错。在拼接时加一层转义
        escaped_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg://{self.DB_USER}:{escaped_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_AGENT_NAME}"

    # 告诉pydantic去哪里去读.env文件
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )


settings = Settings()
