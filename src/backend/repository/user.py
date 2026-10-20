from backend.models.user import UserModel
from backend.repository import BaseRepo
from sqlalchemy import func, select


class UserRepo(BaseRepo):
    """"""

    async def create_user(self, info):
        """创建用户"""
        user = UserModel(**info)
        self.session.add(user)
        await self.session.flush()  # 发SQL,但不关闭事务
        await self.session.refresh(user)  # 此时事务还开着，refresh不会报错
        return user

    async def check_by_id(self, id: str):
        """通过id校验"""
        user = await self.session.scalar(select(UserModel).where(UserModel.id == id))
        return user

    async def check_by_email(self, email: str):
        """邮箱登录"""
        user = await self.session.scalar(
            select(UserModel).where(UserModel.email == email)
        )
        return user

    async def get_by_time(self, time_str: str):
        """获取根据创建日期获取"""
        res = await self.session.execute(
            select(UserModel).where(UserModel.create_at >= time_str)
        )
        users = res.scalars().all()
        return users

    async def get_user_list(self, page: int, size: int, department_id: str | None):
        """获取用户列表"""
        stmt = select(UserModel)
        if department_id:
            stmt = stmt.where(UserModel.department_id == department_id)
        limit = size
        offset = (page - 1) * size
        stmt = stmt.limit(limit).offset(offset).order_by(UserModel.create_at.desc())

        users = await self.session.scalars(stmt)

        return users.all()
