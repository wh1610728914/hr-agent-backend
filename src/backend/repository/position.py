from backend.core.exceptions import BusinessException
from backend.models.positions import PositionModel
from backend.models.user import UserModel
from backend.repository import BaseRepo
from sqlalchemy import func, select


class PositionRepo(BaseRepo):
    async def create_position(self, data):
        """创建职位信息"""
        stmt = select(PositionModel)
        exist_position = await self.session.scalar(
            stmt.where(PositionModel.title == data["title"])
        )
        if exist_position:
            raise BusinessException(message="职位已存在")

        new_position = PositionModel(**data)
        self.session.add(new_position)
        await self.session.flush()
        await self.session.refresh(new_position)
        return new_position

    async def get_position_list(self, page: int, size: int, user: UserModel):
        """获取职位列表"""
        stmt = select(PositionModel)
        # 1.如果是hr，就返回该hr负责的部门
        # 2.如果是其他部门的员工，只要返回该员工所在的部门的职位就好
        # 3.如果是super，全部返回
        if user.is_hr and (not user.is_superuser):
            # 一个hr可以负责多个部门
            department_ids = [d.id for d in user.managed_departments]
            stmt = stmt.where(PositionModel.department_id.in_(department_ids))
        elif (not user.is_hr) and (not user.is_superuser):
            stmt = stmt.where(user.department_id == PositionModel.department_id)

        # 计算分页
        count_stmt = select(func.count()).select_from(
            # subquery 就是刚才那个带条件的查询
            stmt.subquery()
        )
        total = await self.session.scalar(count_stmt)
        # 分页
        stmt = (
            stmt.limit(size)
            .offset((page - 1) * size)
            .order_by(PositionModel.create_at.desc())
        )
        positions = await self.session.scalars(stmt)
        return total, positions.all()
