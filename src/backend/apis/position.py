from backend.dependencies.db import get_db
from backend.dependencies.user import get_current_user, get_super_user
from backend.models.user import UserModel
from backend.repository.position import PositionRepo
from backend.schemas import Response
from backend.schemas.position import PositionRequest
from backend.services.position import (
    getPositionsListService,
    createPositionService,
    delPositionService,
)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/position", tags=["职位"])


@router.get("/list")
async def get_position_list(
    page: int = 1,
    size: int = 10,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取职位列表"""
    res = await getPositionsListService(page, size, user, db)
    return Response.success(data=res)


@router.post("/add")
async def create_position_one(
    data: PositionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建职位信息"""

    res = await createPositionService(data, current_user, db)
    return Response.success(data=res, message="添加成功")


@router.delete("/del/{position_id}")
async def del_position_one(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    """删除职位"""

    res = await delPositionService(position_id, user, db)
    return Response.success(data=res)
