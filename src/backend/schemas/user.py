from datetime import datetime
from typing import Optional

from backend.models.user import UserStatus
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """用户信息"""

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone_number: Optional[str] = Field(..., description="手机号")
    realname: str = Field(..., description="真实姓名")
    avatar: Optional[str] = Field(..., description="头像")
    status: UserStatus = Field(..., description="员工状态")
    is_hr: bool = Field(..., description="是否HR")
    is_superuser: bool = Field(..., description="是否超级用户")
    create_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)
