from backend.repository import BaseRepo
from backend.models.department import DepartmentModel
from sqlalchemy import func, select


class DepartmentRepo(BaseRepo):

    async def create_department(self, info):
        """创建部门"""
        department = DepartmentModel(**info)
        self.session.add(department)
        await self.session.flush()  # 发SQL,但不关闭事务
        await self.session.refresh(department)  # 此时事务还开着，refresh不会报错
        return department

    async def get_by_id(self, id: str):
        """通过id校验"""
        department = await self.session.scalar(
            select(DepartmentModel).where(id == DepartmentModel.id)
        )
        return department

    async def get_by_name(self, name: str) -> str:
        """通过name校验"""
        department = await self.session.scalar(
            select(DepartmentModel).where(name == DepartmentModel.name)
        )
        return department

    async def get_department_list(
        self,
        page: int = 1,
        size: int = 10,
    ):
        """获取部门总列表"""
        stmt = select(DepartmentModel)
        stmt_total = select(func.count(DepartmentModel.id))
        total = await self.session.scalar(stmt_total)
        limit = size
        offset = (page - 1) * size
        stmt = (
            stmt.limit(limit).offset(offset).order_by(DepartmentModel.create_at.desc())
        )
        res = await self.session.scalars(stmt)
        return total, res.all()
