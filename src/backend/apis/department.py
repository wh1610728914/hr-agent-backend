from backend.dependencies.db import get_db
from backend.schemas import Response
from backend.services.department import get_department_list_service
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/depart", tags=["部门方面"])


@router.get("/list", summary="部门列表")
async def get_department_list(
    page: int = 1, size: int = 10, db: AsyncSession = Depends(get_db)
):
    """获取部门总列表"""
    res = await get_department_list_service(page, size, db)
    return Response.success(data=res)
