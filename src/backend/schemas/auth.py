from backend.schemas.user import UserResponse
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """登录请求"""

    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录返回"""

    access_token: str = Field(..., description="")
    refresh_token: str = Field(..., description="")
    user: UserResponse
