from datetime import datetime
from typing import Optional


from openai import BaseModel
from pydantic import ConfigDict, Field
from enum import Enum


class InterviewResultEnum(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


class InterviewSchema(BaseModel):
    """面试记录返回"""

    scheduled_time: Optional[datetime] = Field(default=None, description="面试预定时间")
    feedback: Optional[str] = Field(default=None, description="面试反馈记录")
    result: Optional[InterviewResultEnum] = Field(default=None, description="面试结果")
    candidate_id: Optional[str] = Field(default=None, description="候选人ID")
    interviewer_id: Optional[str] = Field(default=None, description="面试官ID")

    model_config = ConfigDict(from_attributes=True)
