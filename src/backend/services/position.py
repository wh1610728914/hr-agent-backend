from backend.core.exceptions import BusinessException
from backend.dependencies.db import get_db
from backend.dependencies.user import get_super_user
from backend.models.user import UserModel
from backend.repository.position import PositionRepo
from backend.schemas import PageResponse
from backend.schemas.position import (
    PositionRequest,
    PositionResponse,
)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def createPositionService(
    data: PositionRequest, current_user: UserModel, db: AsyncSession
):
    """创建职位信息"""
    # data是pydantic，要给数据库插入，数据库接收的是sqlalchemy（ORM）
    position_repo = PositionRepo(db)
    data_dict = data.model_dump()
    data_dict["creator_id"] = current_user.id
    data_dict["department_id"] = current_user.department_id
    res = await position_repo.create_position(data_dict)
    # 把orm模型转为pydantic
    return PositionResponse.model_validate(res)


async def getPositionsListService(
    page: int, size: int, user: UserModel, db: AsyncSession
):
    """获取职位列表"""
    position_repo = PositionRepo(db)
    total, items = await position_repo.get_position_list(page, size, user)
    return PageResponse(
        total=total, list=[PositionResponse.model_validate(item) for item in items]
    )


async def delPositionService(
    position_id: str,
    user: UserModel,
    db: AsyncSession,
):
    """删除职位
    Service只做业务
    """
    position_repo = PositionRepo(db)
    position = position_repo.get_by_id(position_id)
    if not position:
        raise BusinessException(message="该职位不存在")
    # 不是superuser，或者该部门的员工的话，就不给删除
    if (not user.is_superuser) and (not position.department_id != user.department_id):
        raise BusinessException(message="没有权限删除", code=403)
    res = await position_repo.del_position(position_id)
    return "成功删除"
