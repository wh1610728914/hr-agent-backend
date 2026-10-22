from typing import Optional

from backend.models.candidate import GenderEnum
from pydantic import BaseModel, ConfigDict, Field


class ResumeAgentsResponse(BaseModel):
    """简历大模型输出返回的内容"""

    name: Optional[str] = Field(None, description="候选人姓名")

    gender: GenderEnum = Field(GenderEnum.UNKNOWN, description="候选人性别")

    birthday: Optional[str] = Field(
        None, description="候选人出生日期，如果只有年份，那么就把日期变为1月1日"
    )
    email: Optional[str] = Field(None, description="候选人邮箱")
    phone_number: Optional[str] = Field(None, description="候选人手机号")
    work_experience: Optional[str] = Field(None, description="候选人工作经历")
    project_experience: Optional[str] = Field(None, description="候选人项目经验")
    education_experience: Optional[str] = Field(None, description="候选人教育经历")
    self_evaluation: Optional[str] = Field(None, description="候选人自我评价")
    other_information: Optional[str] = Field(None, description="候选人其他信息")
    skills: Optional[str] = Field(None, description="候选人技能")

    model_config = ConfigDict(from_attributes=True)
