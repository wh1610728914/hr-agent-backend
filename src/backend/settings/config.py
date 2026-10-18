# 配置数据库
from datetime import timedelta
from urllib.parse import quote_plus

# anyio异步库，这里只用来拼接，用异步简直太小题大做了
# from anyio import Path
from pathlib import Path
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # DBTABASE_URL: str | None = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "agent_hr"

    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRES_DAYS: int = 7

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

    # 告诉pydantic去哪里去读.env文件
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )


settings = Settings()
