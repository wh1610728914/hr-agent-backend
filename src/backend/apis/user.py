from backend.dependencies.user import get_cache_invite, get_super_user
from backend.models.user import User
from fastapi import APIRouter, BackgroundTasks, Depends

from backend.schemas.user import InviteUserRequest
from backend.core.cache import HRCache
from backend.dependencies.db import get_db

router = APIRouter(prefix="/user", tags=["用户方面"])


@router.post("/invite", summary="邀请用户")
async def invite_user(
    invite_data: InviteUserRequest,
    background_tasks: BackgroundTasks,
    session=Depends(get_db),
    cache: HRCache = Depends(get_cache_invite),
    _: User = Depends(get_super_user),
):
    """
    当前登录的用户是超级用户才可以发送邀请码
    """
