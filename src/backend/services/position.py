from backend.models.user import UserModel
from backend.repository.position import PositionRepo
from backend.schemas import PageResponse
from backend.schemas.position import PositionRequest, PositionResponse
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


async def getPositionsListService(page: int, size: int, db: AsyncSession):
    """获取职位列表"""
    position_repo = PositionRepo(db)
    total, items = await position_repo.get_position_list(page, size)
    return PageResponse(
        total=total, list=[PositionResponse.model_validate(item) for item in items]
    )
