from datetime import datetime
from typing import List, Optional

from backend.models.user import UserStatus
from backend.schemas.department import DepartmentResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """用户信息"""

    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone_number: Optional[str] = Field(..., description="手机号")
    realname: str = Field(..., description="真实姓名")
    avatar: Optional[str] = Field(..., description="头像")
    status: UserStatus = Field(..., description="员工状态")
    is_hr: bool = Field(..., description="是否HR")
    is_superuser: bool = Field(..., description="是否超级用户")
    create_at: datetime = Field(..., description="创建时间")

    department: DepartmentResponse = Field(..., description="所属部门")
    model_config = ConfigDict(from_attributes=True)


class InviteUserRequest(BaseModel):
    """发送邀请码请求参数"""

    email: EmailStr = Field(..., description="邮箱")
    department_id: str = Field(..., description="部门id")


class IncreaseDays7Li(BaseModel):
    create_at: datetime
    count: int = 0
    model_config = ConfigDict(from_attributes=True)


class IncreaseDays7Response(BaseModel):
    """获取7天内的候选人"""

    list: List[IncreaseDays7Li]


class UpdateUserStatusRequest(BaseModel):
    """修改员工状态"""

    user_id: str = Field(..., description="用户ID")
    status: UserStatus = Field(..., description="员工状态")


class SetDingUserRequest(BaseModel):
    """设置钉钉的用户信息"""

    nick: str = Field(..., description="昵称")
    union_id: str
    open_id: str
    mobile: str
