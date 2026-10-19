from datetime import datetime, timedelta
from backend.schemas import PageResponse
from backend.schemas.user import IncreaseDays7Response, UserResponse
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
    # get_user_list
    user_repo = UserRepo(db)
    res = await user_repo.get_user_list(page, size, department_id)
    return PageResponse(
        total=len(res), list=[UserResponse.model_validate(item) for item in res]
    )
