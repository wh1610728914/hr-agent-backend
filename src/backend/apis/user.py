from backend.dependencies.user import get_cache_invite, get_super_user
from backend.models.user import UserModel
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.user import InviteUserRequest
from backend.core.cache import HRCache
from backend.dependencies.db import get_db
from backend.services.auth import inviteCodeService
from backend.schemas import Response

router = APIRouter(prefix="/user", tags=["用户方面"])


@router.post("/invite", summary="邀请用户", response_model=Response)
async def invite_user(
    data: InviteUserRequest,
    background_tasks: BackgroundTasks,  # 这就是告诉后台执行
    db: AsyncSession = Depends(get_db),  # 数据库
    cache: HRCache = Depends(get_cache_invite),  # redis缓存
    _: UserModel = Depends(get_super_user),
):
    """
    当前登录的用户是超级用户才可以发送邀请码
    """
    res = await inviteCodeService(data, background_tasks, db, cache)
    return Response.success(data=res)
