from backend.core.exceptions import BusinessException
from backend.models.user import UserModel
from backend.repository.department import DepartmentRepo
from backend.repository.user import UserRepo
from backend.schemas import PageResponse
from backend.schemas.hr import AssignDepartmentRequest
from backend.schemas.user import UserResponse
from sqlalchemy.ext.asyncio import AsyncSession


async def getHrListService(page: int, size: int, db: AsyncSession):
    user_repo = UserRepo(db)
    res = await user_repo.get_by_hr(page, size)
    return PageResponse(
        total=len(res), list=[UserResponse.model_validate(item) for item in res]
    )


async def assignDepartmentService(data: AssignDepartmentRequest, db: AsyncSession):
    """给hr分配指定的部门"""
    user_repo = UserRepo(db)
    try:
        res = await user_repo.assign_departs(data)
    except Exception as e:
        raise BusinessException(message=e)
    return "分配成功"
