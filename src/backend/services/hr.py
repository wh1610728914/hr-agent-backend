from backend.core.exceptions import BusinessException
from backend.models.user import UserModel
from backend.repository.department import DepartmentRepo
from backend.repository.user import UserRepo
from backend.schemas.hr import AssignDepartmentRequest
from sqlalchemy.ext.asyncio import AsyncSession


async def assignDepartmentService(data: AssignDepartmentRequest, db: AsyncSession):
    """给hr分配指定的部门"""
    user_repo = UserRepo(db)
    try:
        res = await user_repo.assign_departs(data)
    except Exception as e:
        raise BusinessException(message=e)
    return "分配成功"
