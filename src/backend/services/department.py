from backend.dependencies.db import get_db
from backend.repository.department import DepartmentRepo
from backend.schemas import PageResponse
from backend.schemas.department import DepartmentResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def get_department_list_service(
    page: int, size: int, db: AsyncSession = Depends(get_db)
):
    """获取部门列表"""
    depart_repo = DepartmentRepo(db)
    total, res = await depart_repo.get_department_list(page, size)
    return PageResponse(
        total=total, list=[DepartmentResponse.model_validate(item) for item in res]
    )
