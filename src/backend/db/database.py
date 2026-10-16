# 连接数据库
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.settings import settings
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Integer, MetaData
from datetime import datetime

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # 连接池大小（默认是5个）
    pool_size=10,
    # 允许连接池最大的连接数（默认是10个）
    max_overflow=20,
    # 获得连接超时时间（默认是30s）
    pool_timeout=10,
    # 连接回收时间（默认是-1，代表永不回收）
    pool_recycle=3600,
    # 连接前是否预检查（默认为False）
    pool_pre_ping=True,
)

# 配置会话工厂
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # 提交事务后,不要让session里面的对象过期,默认true,过期的话,再获取就会再查询一遍
    expire_on_commit=False,
    # 不自动提交事务
    autocommit=False,
    # 不自动刷新
    autoflush=False,
)


# 固定名称格式！！
class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


# 两层继承
class BaseTable(Base):
    # 我这个是抽象类，别给我真正建表哦！！！
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="主键id",
        sort_order=-1,
        autoincrement=True,  # 自增
    )
    create_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    update_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
