from backend.models.candidate import ResumeModel
from backend.models.user import UserModel
from backend.repository import BaseRepo


class CandidateRepo(BaseRepo):

    async def upload_resume(self, file_path: str, uploader_id: str):
        """上传简历"""
        resume = ResumeModel(file_path=str(file_path), uploader_id=uploader_id)
        self.session.add(resume)
        await self.session.flush()
        await self.session.refresh(resume)
        return resume
