from typing import List, Optional

from backend.db.database import BaseTable
from backend.core import password
from sqlalchemy import Boolean, ForeignKey, String, Enum as SEnum, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from backend.models.association_tables import user_department

# from backend.models.department import DepartmentModel


class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"  # 在职
    BLOCKED = "BLOCKED"  # 被锁定
    RESIGNED = "RESIGNED"  # 已离职


class UserModel(BaseTable):
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
    avatar: Mapped[str | None] = mapped_column(
        String(255), comment="头像", nullable=True
    )
    status: Mapped[UserStatus] = mapped_column(
        SEnum(UserStatus), default=UserStatus.ACTIVE, comment="用户状态"
    )
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否是hr")
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否是超级用户"
    )
    # department:
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id"))

    # 在DepartmentModel 这个类，有一个叫 members的属性，就代表了我（UserModel)
    # 一对多
    department: Mapped[Optional["DepartmentModel"]] = relationship(
        # 双向绑定的声明
        back_populates="members",
        # 用哪个外键来连接这两个表
        foreign_keys=[department_id],
        # 默认select：查出一个User时，不会立刻去查部门信息， 只有写了user.department.name才去查 -- 懒加载
        # joined ：直接发出查询！立刻同步
        lazy="joined",
    )

    # 多对多
    managed_departments: Mapped[List["DepartmentModel"]] = relationship(
        # 告诉sqlalchemy ：我们是多对多的，你去查user_department这张中间表
        secondary=user_department,
        back_populates="managing_hrs",
    )
    # 一对一
    dingding_user: Mapped["DingDingModel"] = relationship(
        back_populates="user",
        # false 表示 返回的是 单个对象，而不是一个列表，通常适用于 一对一
        uselist=False,
        # 如果是True的话，表示返回的是一个列表，一对多
    )

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
