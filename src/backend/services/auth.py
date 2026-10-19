import random
import string

from fastapi import BackgroundTasks

from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import InviteUserRequest, UserResponse
from backend.core.exceptions import BusinessException
from backend.core.token import AuthHandler
from backend.core.password import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.repository.user import UserRepo
from backend.repository.department import DepartmentRepo
from backend.core.cache import HRCache, InviteInfoSchema
from backend.tasks.email_task import send_invite_email_task


async def loginEmailService(
    data: LoginRequest, db: AsyncSession, authToken: AuthHandler
):
    """登录 -- 操作数据库"""
    repo = UserRepo(db)
    user = await repo.check_by_email(str(data.email))
    if not user:
        raise BusinessException(message="该用户不存在")
    if not verify_password(data.password, user.password):
        raise BusinessException(message="邮箱或密码错误")

    # 获取token
    tokens = authToken.encode_login_token(user.id)
    resToken = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": UserResponse.model_validate(user),
    }
    return LoginResponse(**resToken)


async def inviteCodeService(
    data: InviteUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    cache: HRCache,
):
    """发送邀请码"""
    user_repo = UserRepo(db)
    user = await user_repo.check_by_email(str(data.email))
    if user:
        raise BusinessException(message="该邮箱已被注册")

    department_repo = DepartmentRepo(db)
    department = await department_repo.get_by_id(data.department_id)
    if not department:
        raise BusinessException(message="该部门不存在")

    # 生成6位数验证码
    invite_code = "".join(random.sample(string.digits, 6))
    # 存储到redis缓存中
    invite_info = InviteInfoSchema(
        email=data.email, department_id=data.department_id, invite_code=invite_code
    )
    await cache.set_invite_info(invite_info)
    # 发送邮件
    background_tasks.add_task(  # 告诉：后台去运行
        send_invite_email_task, str(invite_info.email), invite_code
    )
    return "发送成功"
