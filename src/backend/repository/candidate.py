from backend.core.exceptions import BusinessException
from backend.models.candidate import CandidateModel, ResumeModel
from backend.models.user import UserModel
from backend.repository import BaseRepo
from backend.schemas.candidate import CreateCandidateRequest
from sqlalchemy import select


class ResumeRepo(BaseRepo):

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


class CandidateRepo(BaseRepo):
    """候选人repo"""

    async def create_candidate(self, user, data):
        """创建候选人"""
        # 字典解包实例化orm模型 ,直接解包给数据库
        candidateInfo = CandidateModel(**data)
        candidateInfo.creator_id = user.id
        self.session.add(candidateInfo)
        await self.session.flush()
        await self.session.refresh(candidateInfo)
        return "创建成功"
