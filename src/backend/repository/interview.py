from backend.models.interview import InterviewModel
from backend.repository import BaseRepo


class Interview(BaseRepo):
    async def create_interview_repo(self, data):
        # data dump格式
        interview = InterviewModel(**data)
        self.session.add(data)
        await self.session.flush()
        await self.session.refresh()
        return "添加成功"
