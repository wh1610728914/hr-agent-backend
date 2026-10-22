from backend.core.exceptions import BusinessException
from backend.models.candidate import ResumeModel
from backend.models.user import UserModel
from backend.repository import BaseRepo
from sqlalchemy import select


class CandidateRepo(BaseRepo):

    async def upload_resume(self, file_path: str, uploader_id: str):
        """上传简历"""
        resume = ResumeModel(file_path=str(file_path), uploader_id=uploader_id)
        self.session.add(resume)
        await self.session.flush()
        await self.session.refresh(resume)
        return resume

    async def by_get_id(self, id: str):
        """通过id获取简历"""
        resume = await self.session.scalar(
            select(ResumeModel).where(id == ResumeModel.id)
        )
        if not resume:
            raise BusinessException(message="该简历不存在")
        return resume
