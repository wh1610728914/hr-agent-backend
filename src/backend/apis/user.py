from backend.dependencies.user import get_cache_invite, get_super_user
from backend.models.user import UserModel
from backend.services.user import increaseDays7CandidatesService, getUserListService
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


@router.get("/increaseDays", summary="获取7天内增加的候选人")
async def getIncreaseDays7(db: AsyncSession = Depends(get_db)):
    """获取指定时间内增加的候选人"""
    res = await increaseDays7CandidatesService(db)
    return Response.success(data=res)


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
