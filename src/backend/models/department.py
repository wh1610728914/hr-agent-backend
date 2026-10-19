from typing import List, Optional

from sqlalchemy import String

from backend.db.database import BaseTable
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.association_tables import user_department

# from backend.models.user import UserModel


class DepartmentModel(BaseTable):
    __tablename__ = "departments"
    __table_args__ = {"comment": "部门信息表"}

    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="部门名称"
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="部门描述")

    members: Mapped[List["UserModel"]] = relationship(back_populates="department")

    managing_hrs: Mapped[List["UserModel"]] = relationship(
        secondary=user_department, back_populates="managed_departments"
    )
