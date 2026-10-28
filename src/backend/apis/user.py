from backend.dependencies.user import (
    get_cache_instance,
    get_current_user,
    get_super_user,
)
from backend.models.user import UserModel
from backend.services.user import (
    getUserListService,
    updateUserStatusService,
)
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.user import (
    InviteCodeRequest,
    UpdateUserStatusRequest,
)
from backend.core.cache import HRCache
from backend.dependencies.db import get_db
from backend.services.user import inviteCodeService
from backend.schemas import Response

router = APIRouter(prefix="/user", tags=["用户方面"])


@router.get("/list", summary="获取员工列表")
async def getUserList(
    page: int = 1,
    size: int = 10,
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_super_user),
):
    """获取员工列表"""
    res = await getUserListService(page, size, department_id, db)
    return Response.success(data=res)


@router.patch("/update/status", summary="修改员工状态")
async def updateUserStatus(
    data: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_super_user),
):
    """修改员工状态"""
    res = await updateUserStatusService(data, db)
    return Response.success(data=res)


@router.post("/invitecode", summary="员工给新用户发送邀请码")
async def sendInviteCode(
    data: InviteCodeRequest,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    _: UserModel = Depends(get_super_user),
    db: AsyncSession = Depends(get_db),
    cache: HRCache = Depends(get_cache_instance),
):
    res = await inviteCodeService(data, user, db, cache, background_tasks)
    return Response.success(data=res)
