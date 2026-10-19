from backend.models.user import UserModel
from backend.repository import BaseRepo
from sqlalchemy import select


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
