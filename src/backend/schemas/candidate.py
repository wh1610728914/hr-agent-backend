from typing import Optional

from backend.models.candidate import GenderEnum
from backend.schemas.user import UserResponse
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """简历返回"""

    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历路径")
    uploader: UserResponse = Field(..., description="上传者")

    model_config = ConfigDict(from_attributes=True)


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
