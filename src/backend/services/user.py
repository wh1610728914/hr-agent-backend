from datetime import datetime, timedelta
import secrets
from uuid import uuid4
from backend.core.cache import HRCache, InviteInfoSchema
from backend.core.exceptions import BusinessException
from backend.models.user import UserModel
from backend.repository.department import DepartmentRepo
from backend.schemas import PageResponse
from backend.schemas.user import (
    IncreaseDays7Response,
    InviteCodeRequest,
    UpdateUserStatusRequest,
    UserResponse,
)
from backend.tasks.email_task import send_invite_email_task
from fastapi import BackgroundTasks
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
    total, res = await user_repo.get_user_list(page, size, department_id)
    return PageResponse(
        total=total, list=[UserResponse.model_validate(item) for item in res]
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


async def inviteCodeService(
    data: InviteCodeRequest,
    user: UserModel,
    db: AsyncSession,
    cache: HRCache,
    background_tasks: BackgroundTasks,
):
    """员工给新用户发送邀请码"""
    user_repo = UserRepo(db)
    userInfo = await user_repo.check_by_email(data.email)
    if userInfo:
        raise BusinessException(message="已存在相关用户")

    department_repo = DepartmentRepo(db)
    department = await department_repo.get_by_id(user.department_id)
    if not department:
        raise BusinessException(message="该部门不存在，请重试")

    # 生成邀请码
    invite_code = "".join(
        # secrets.choice 是密码学安全的随机选择
        secrets.choice("0123456789")
        # _ 我不关心这个变量的名字，我只是需要循环6次而已
        for _ in range(6)
    )

    # 要把邀请码给redis缓存
    invite_info = {"invite_code": invite_code, "email": data.email}
    await cache.set_invite_code(
        InviteInfoSchema(
            email=data.email, invite_code=invite_code, department_id=data.department_id
        )
    )
    # 给指定邮箱发送 -- 后台任务
    background_tasks.add_task(
        send_invite_email_task, email=data.email, invite_code=invite_code
    )
    return "发送成功"
