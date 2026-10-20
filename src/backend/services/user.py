from datetime import datetime, timedelta
from backend.core.exceptions import BusinessException
from backend.schemas import PageResponse
from backend.schemas.user import (
    IncreaseDays7Response,
    SetDingUserRequest,
    UpdateUserStatusRequest,
    UserResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession
from backend.repository.user import UserRepo


async def increaseDays7CandidatesService(
    db: AsyncSession,
):
    """近7天新增候选人"""
    now = datetime.now()
    # 获取今天的 00:00:00，减去 7 天，得到 7天前的 00:00:00
    start_time = datetime(now.year, now.month, now.day) - timedelta(days=7)

    user_repo = UserRepo(db)
    res = await user_repo.get_by_time(start_time)
    return IncreaseDays7Response(list=res)


async def getUserListService(
    page: int, size: int, department_id: str | None, db: AsyncSession
):
    """获取用户列表"""
    user_repo = UserRepo(db)
    res = await user_repo.get_user_list(page, size, department_id)
    return PageResponse(
        total=len(res), list=[UserResponse.model_validate(item) for item in res]
    )


async def updateUserStatusService(data: UpdateUserStatusRequest, db: AsyncSession):
    """修改员工状态"""

    user_repo = UserRepo(db)
    user = await user_repo.check_by_id(data.user_id)
    if not user:
        raise BusinessException(message="该用户不存在")
    if user.is_superuser:
        raise BusinessException(message="不可修改超级用户的状态")
    user.status = data.status
    return "修改成功"
