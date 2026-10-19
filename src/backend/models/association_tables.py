# 关联表 （many-to-many)
from sqlalchemy import Column, ForeignKey, Table

from backend.db.database import Base

# 用户和部门表的多对多
user_department = Table(  # Table 关联表
    "user_department",  # 数据库里中间表的名字
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("department_id", ForeignKey("departments.id"), primary_key=True),
)
