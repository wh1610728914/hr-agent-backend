from backend.schemas.user import UserResponse
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """简历返回"""

    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历路径")
    uploader: UserResponse = Field(..., description="上传者")

    model_config = ConfigDict(from_attributes=True)
