from backend.repository.user import UserRepo
from backend.schemas.user import DingUserResponse
from sqlalchemy.ext.asyncio import AsyncSession


async def getDingInfoService(user_id: str, db: AsyncSession):
    user_repo = UserRepo(db)
    res = await user_repo.get_ding_info_repo(user_id)
    # model_validate 验证并转换模型
    return DingUserResponse.model_validate(res)
