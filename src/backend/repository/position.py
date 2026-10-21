from backend.core.exceptions import BusinessException
from backend.models.positions import PositionModel
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

    async def get_position_list(self, page: int, size: int):
        """获取职位列表"""
        stmt = select(PositionModel)
        stmt_total = select(func.count(PositionModel.id))
        total = await self.session.scalar(stmt_total)
        limit = size
        offset = (page - 1) * size
        stmt = stmt.limit(limit).offset(offset).order_by(PositionModel.create_at.desc())
        postions = await self.session.scalars(stmt)

        return total, postions.all()
