from backend.core.exceptions import BusinessException
from backend.models.candidate import CandidateAIScoreModel, CandidateModel, ResumeModel
from backend.models.user import UserModel
from backend.repository import BaseRepo
from backend.schemas.candidate import CreateCandidateRequest

from sqlalchemy import func, select


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
        # candidate = await self.session.scalar(
        #     select(CandidateModel).where(CandidateModel.email == data["email"])
        # )
        # if candidate:
        #     raise BusinessException(message="该候选人不可重复添加")
        # 字典解包实例化orm模型 ,直接解包给数据库
        candidateInfo = CandidateModel(**data)
        candidateInfo.creator_id = user.id
        self.session.add(candidateInfo)
        await self.session.flush()
        await self.session.refresh(
            candidateInfo, attribute_names=["position", "creator"]
        )
        return candidateInfo

    async def create_ai_scope(self, candidate_id, candidate_scope_dict):
        """创建ai得分"""
        aiScopeInfo = CandidateAIScoreModel(
            candidate_id=candidate_id, **candidate_scope_dict
        )
        self.session.add(aiScopeInfo)
        await self.session.flush()
        await self.session.refresh(aiScopeInfo)
        return "创建成功"

    async def by_get_id(self, id):
        """通过id获取候选人"""
        candidate = await self.session.scalar(
            select(CandidateModel).where(id == CandidateModel.id)
        )
        if not candidate:
            raise BusinessException(message="对应的候选人不存在")

        return candidate

    async def update_candidate_status(self, candidate, val):
        """修改候选人状态"""
        # candidate = await self.by_get_id(id)
        # if not candidate:
        #     raise BusinessException(message="没有对应的候选人")
        candidate.status = val

        return candidate

    async def get_candidate_list(self, page, size, keyword):
        """获取候选人列表"""

        if keyword:
            pass

        total = await self.session.scalar(func.count(CandidateModel.id))
        offset = (page - 1) * size
        if offset >= total:
            return total, []
        stmt = (
            select(CandidateModel)
            .order_by(CandidateModel.create_at.desc())
            .limit(size)
            .offset((page - 1) * size)
        )
        candidate_list = await self.session.scalars(stmt)
        return total, candidate_list.all()

    async def get_score_candidate(self, id):
        """获取候选人ai得分情况"""
        stmt = select(CandidateAIScoreModel).where(
            id == CandidateAIScoreModel.candidate_id
        )
        score_candi = await self.session.scalar(stmt)
        return score_candi
