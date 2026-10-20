from backend.dependencies.db import get_db
from backend.dependencies.user import get_super_user
from backend.models.user import UserModel
from backend.schemas import Response
from backend.schemas.hr import AssignDepartmentRequest
from backend.services.hr import assignDepartmentService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/hr", tags=["HR"])


@router.post("/assign/department", summary="给hr指派部门")
async def assign_department(
    data: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_super_user),
):
    # 首先是hr
    # 其实给它们指派 不同的部门 只能super分配
    res = await assignDepartmentService(data, db)
    return Response.success(data=res)
