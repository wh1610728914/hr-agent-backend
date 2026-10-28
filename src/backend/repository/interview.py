from typing import Any, Optional

from backend.models.candidate import CandidateStatusEnum
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
        """获取面试信息"""
        res = await self.session.scalar(
            select(InterviewModel).where(InterviewModel.candidate_id == candidate_id)
        )
        return res

    async def update_interview_status_repo(self, data: dict[str, Any]):
        """更改面试状态"""
        interview_info = await self.session.scalar(
            select(InterviewModel).where(InterviewModel.id == id)
        )
        interview_info.result = data.status
        if data.status == CandidateStatusEnum.INTERVIEW_REJECTED:
            # 拒绝面试就要传未通过理由
            interview_info.feedback = data.reason
        await self.session.flush()
        await self.session.refresh(interview_info)
        return interview_info
