# 必须是superUser 才可以邀请
from functools import lru_cache

from backend.models.user import UserModel, UserStatus
from backend.repository.user import UserRepo
from backend.core.exceptions import BusinessException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies.db import get_db
from backend.dependencies.token import get_auth_handler
from fastapi import Depends
from backend.core.cache import HRCache

authToken = get_auth_handler()


async def get_user_id(iss: str = Depends(authToken.auth_access_dependency)):
    """获取用户ID"""
    return iss


async def get_current_user(
    iss: str = Depends(get_user_id), session: AsyncSession = Depends(get_db)
):
    """是否是当前登录的用户"""
    user_id = str(iss)
    user_repo = UserRepo(session)
    user = await user_repo.check_by_id(user_id)
    if not user:
        raise BusinessException(message="该用户不存在")
    if user.status != UserStatus.ACTIVE:
        raise BusinessException(message="该员工状态不可用，请联系管理员")
    return user


def get_super_user(current_user: UserModel = Depends(get_current_user)):
    """
    判断当前用户是否是超级用户
    """
    if not current_user.is_superuser:
        raise BusinessException(code=403, message="权限不足，只有超级用户才可以邀请")

    return current_user


@lru_cache(maxsize=1)  # 单例
def get_cache_invite():
    """把邀请信息相关的也变成依赖进入"""
    return HRCache()
