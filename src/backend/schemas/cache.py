from typing import Literal

from backend.schemas.agents import ResumeAgentsResponse
from pydantic import BaseModel, ConfigDict, EmailStr


class InviteInfoSchema(BaseModel):
    """邀请码"""

    department_id: str
    email: EmailStr
    invite_code: str


class DingTalkTokenInfoSchema(BaseModel):
    """dingding存储的"""

    access_token: str
    refresh_token: str
    user_id: str


class OCRInfoSchema(BaseModel):
    """ocr解析文档"""

    task_id: str
    status: Literal["running", "done", "failed"]
    error: str | None = None
    res: ResumeAgentsResponse | None = None
