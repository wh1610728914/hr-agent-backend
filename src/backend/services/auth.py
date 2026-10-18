from backend.models.user import User
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserResponse
from backend.utils.exceptions import BusinessException
from backend.utils.jwt import AuthHandler
from backend.utils.password import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.repository.auth import UserRepo


async def loginEmailService(
    data: LoginRequest, db: AsyncSession, authToken: AuthHandler
):
    """登录 -- 操作数据库"""
    repo = UserRepo(db)
    user = await repo.login_email(str(data.email))
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
