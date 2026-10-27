from typing import Optional

from backend.models.candidate import CandidateStatusEnum, GenderEnum
from backend.schemas.position import PositionResponse, PositionSchema
from backend.schemas.user import UserResponse, UserSchema
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """简历返回"""

    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历路径")
    uploader: UserResponse = Field(..., description="上传者")

    model_config = ConfigDict(from_attributes=True)


class ResumeSchema(ResumeResponse):
    pass


class ResumeParseRequest(BaseModel):
    """解析简历Request"""

    resume_id: str = Field(..., description="简历ID")


class ResumeParseResponse(BaseModel):
    """解析简历Response"""

    task_id: str = Field(..., description="任务ID")

    model_config = ConfigDict(from_attributes=True)


class CreateCandidateRequest(BaseModel):
    """创建候选人request"""

    name: str = Field(..., description="候选人姓名")
    email: str = Field(..., description="候选人邮箱")
    gender: GenderEnum = Field(GenderEnum.UNKNOWN, description="候选人性别")
    birthday: Optional[str] = Field(
        None, description="候选人出生日期，如果只有年份，那么就把日期变为1月1日"
    )
    phone_number: Optional[str] = Field(None, description="候选人手机号")
    work_experience: Optional[str] = Field(None, description="候选人工作经历")
    project_experience: Optional[str] = Field(None, description="候选人项目经验")
    education_experience: Optional[str] = Field(None, description="候选人教育经历")
    self_evaluation: Optional[str] = Field(None, description="候选人自我评价")
    other_information: Optional[str] = Field(None, description="候选人其他信息")
    skills: Optional[str] = Field(None, description="候选人技能")
    position_id: str = Field(..., description="投递的职位ID")
    resume_id: str = Field(..., description="简历ID")


class CandidateSchema(BaseModel):
    """候选人"""

    id: str
    name: str = Field(..., description="候选人姓名")
    email: str = Field(..., description="候选人邮箱")
    gender: GenderEnum = Field(GenderEnum.UNKNOWN, description="候选人性别")
    birthday: Optional[str] = Field(
        None, description="候选人出生日期，如果只有年份，那么就把日期变为1月1日"
    )
    phone_number: Optional[str] = Field(None, description="候选人手机号")
    work_experience: Optional[str] = Field(None, description="候选人工作经历")
    project_experience: Optional[str] = Field(None, description="候选人项目经验")
    education_experience: Optional[str] = Field(None, description="候选人教育经历")
    self_evaluation: Optional[str] = Field(None, description="候选人自我评价")
    other_information: Optional[str] = Field(None, description="候选人其他信息")
    skills: Optional[str] = Field(None, description="候选人技能")
    status: CandidateStatusEnum = Field(
        CandidateStatusEnum.APPLICATION, description="候选人状态"
    )
    position: PositionSchema = Field(..., description="投递的职位信息")
    resume: ResumeSchema = Field(..., description="简历信息")
    creator: UserSchema = Field(..., description="创建该候选人的员工信息")

    model_config = ConfigDict(from_attributes=True)


class CandidateAIScopeSchema(BaseModel):
    """候选人ai评分后返回的格式"""

    id: str
    work_experience_score: int = Field(..., description="工作经验得分")
    technical_skills_score: int = Field(..., description="技术能力得分")
    soft_skills_score: int = Field(..., description="软技能得分")
    educational_background_score: int = Field(..., description="教育背景得分")
    project_experience_score: int = Field(..., description="项目经验得分")
    overall_score: int = Field(..., description="综合总分(各维度加权/汇总)")
    summary: str = Field(..., description="综合评价摘要")
    strengths: list[str] = Field(..., description="优势(JSON 字符串数组)")
    weaknesses: list[str] = Field(..., description="劣势/待改进点(JSON 字符串数组)")

    model_config = ConfigDict(from_attributes=True)
