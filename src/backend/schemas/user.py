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


class UserSchema(UserResponse):
    pass


class InviteCodeRequest(BaseModel):
    """发送邀请码给新用户"""

    email: EmailStr = Field(..., description="邮箱")
    department_id: str = Field(..., description="员工发送邀请码时所属的部门")


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


class DingUserResponse(BaseModel):
    """钉钉的用户信息"""

    id: str = Field(..., description="钉钉账号在自己服务器上的id")
    nick: str = Field(..., description="在钉钉上昵称")
    union_id: str = Field(..., description="在钉钉上union_id")
    open_id: str = Field(..., description="在钉钉上open_id")
    mobile: str = Field(..., description="在钉钉上mobile")
    user_id: str = Field(..., description="在钉钉上的用户表的外键")
    model_config = ConfigDict(from_attributes=True)
