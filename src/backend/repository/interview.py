from backend.models.interview import InterviewModel
from backend.repository import BaseRepo
from sqlalchemy import select


class Interview(BaseRepo):
    async def create_interview_repo(self, data):
        # data dump格式
        interview = InterviewModel(**data)
        self.session.add(interview)
        await self.session.flush()
        await self.session.refresh(interview)
        return "添加成功"

    async def get_interview_repo(self, candidate_id: str):
        res = await self.session.scalar(
            select(InterviewModel).where(InterviewModel.candidate_id == candidate_id)
        )
        return res
