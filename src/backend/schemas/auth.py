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


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr = Field(..., description="邮箱")
    invite_code: str = Field(..., description="邀请码", min_length=6, max_length=6)
    username: str = Field(..., description="用户名")
    realname: str = Field(..., description="真实姓名")
    password: str = Field(..., description="密码")
