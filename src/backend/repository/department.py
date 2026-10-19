from backend.repository import BaseRepo


class DepartmentRepo(BaseRepo):
    async def get_by_id(self, id: str):
        """通过id校验"""
        department = await self.session.scalar(select(De))
