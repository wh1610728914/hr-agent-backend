from backend.models.user import User
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import InviteUserRequest, UserResponse
from backend.core.exceptions import BusinessException
from backend.core.jwt import AuthHandler
from backend.core.password import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.backend.repository.user import UserRepo


async def loginEmailService(
    data: LoginRequest, db: AsyncSession, authToken: AuthHandler
):
    """登录 -- 操作数据库"""
    repo = UserRepo(db)
    user = await repo.check_by_id(str(data.email))
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


async def inviteCodeService(data: InviteUserRequest, db: AsyncSession):
    """发送邀请码"""
    user_repo = UserRepo(db)
    user = await user_repo.check_by_id(str(data.email))
    if user:
        raise BusinessException(message='该邮箱已被注册')

    department_repo = 
