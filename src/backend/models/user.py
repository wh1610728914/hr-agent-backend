from typing import Optional

from backend.db.database import BaseTable
from backend.utils import password
from sqlalchemy import Boolean, String, Enum as SEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum


class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"  # 在职
    BLOCKED = "BLOCKED"  # 被锁定
    RESIGNED = "RESIGNED"  # 已离职


class User(BaseTable):
    """用户信息表"""

    __tablename__ = "users"
    __table_args__ = {"comment": "用户信息表"}

    username: Mapped[str] = mapped_column(
        String(50),
        #  unique:数据不可重复
        unique=True,
        # index：建立数据库索引，快速查询（经常出现在where条件里面的字段或者用于 order by排序的字段）
        index=True,
        nullable=False,
        comment="用户名",
    )
    _password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    email: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="邮箱"
    )
    # Optional[str] 可以是str 也可以是None
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, index=True, comment="手机号"
    )
    realname: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="真实姓名"
    )
    avatar: Mapped[str] = mapped_column(String(255), comment="头像")
    status: Mapped[UserStatus] = mapped_column(
        SEnum(UserStatus), default=UserStatus.ACTIVE, comment="用户状态"
    )
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否是hr")
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否是超级用户"
    )
    # department:

    # 好处是 自动匹配，自动加密
    def __init__(self, **kw):
        if "password" in kw:
            # 取出password的值，并把它从kw上删除掉
            raw_password = kw.pop("password")
            kw["_password"] = password.hash_password(raw_password)
        super().__init__(**kw)

    # @property 把一个方法伪装成属性对象来访问
    @property
    def password(self):
        """访问user.password，取得是 _password的值"""
        return self._password

    @password.setter  # 这个对象有一个方法叫setter，名字必须和上面的一样
    def password(self, pwd):
        """
        给user.password赋值的话，自动调用这个方法
        修改密码自动加密
        """
        self._password = password.hash_password(pwd)
