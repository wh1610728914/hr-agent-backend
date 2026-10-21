from datetime import datetime
import enum
from typing import Optional

from backend.db.database import BaseTable
from backend.models.department import DepartmentModel
from backend.models.user import UserModel
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SqlEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EducationEnum(enum.Enum):
    # 1. 大专
    COLLEGE = "大专"
    # 2. 本科
    BACHELOR = "本科"
    # 3. 硕士
    MASTER = "硕士"
    # 4. 博士
    DOCTOR = "博士"
    # 5. 未填写
    UNKNOWN = "未知"


class PositionModel(BaseTable):
    __tablename__ = "positions"
    __table_args__ = {"comment": "职位表"}

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    recruitment_count: Mapped[int] = mapped_column(Integer, default=1)
    # 最低学历要求
    education: Mapped[EducationEnum] = mapped_column(
        SqlEnum(EducationEnum),
        default=EducationEnum.UNKNOWN,
        nullable=False,
        comment="学历",
    )
    # 最低工作年限要求
    work_year: Mapped[int] = mapped_column(Integer, default=0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    # ForeignKey外键在哪里，哪里就是多的一方
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    creator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    # 没加back_populates 那就表示不用双向绑定
    department: Mapped["DepartmentModel"] = relationship(lazy="joined")
    creator: Mapped["UserModel"] = relationship(
        # selectin 优化查询职位列表过慢情况，在主查询执行后，发出一条IN()的sql去批量加载关联数据
        lazy="selectin"
    )
