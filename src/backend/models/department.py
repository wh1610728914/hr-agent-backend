from backend.db.database import BaseTable


class Department(BaseTable):
    __tablename__ = "departments"
    __table_args__ = {"comment": "部门信息表"}
