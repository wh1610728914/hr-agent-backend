# 缓存


from datetime import timedelta

from backend.settings import settings
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache
from pydantic import BaseModel, EmailStr


# redis缓存
class InviteInfoSchema(BaseModel):
    email: EmailStr
    department_id: str
    invite_code: str


class DingTalkTokenInfoSchema(BaseModel):
    """dingding存储的"""

    access_token: str
    refresh_token: str
    user_id: str


# HRCache
class HRCache:
    """管理HR邀请信息的缓存"""

    invite_prefix = "invite:"  # key前缀，用于命名空间隔离
    dingding_prefix = "dings:"

    def __init__(self):
        # 获取lifespan中初始化的redis后端
        self.cache_backend: RedisBackend = FastAPICache.get_backend()

    # ================ 基础方法 ===================================
    async def set(self, key: str, value: dict, ex: int):
        """存"""
        await self.cache_backend.set(key, value, expire=ex if ex else None)

    async def get(self, key: str):
        """获取"""
        value = await self.cache_backend.get(key)
        return value

    async def delete(self, key: str):
        """删除指定的key，
        千万别用clear -》 那个是清空整个Redis数据库！！！
        """
        await self.cache_backend.delete(key)

    # ================ 邀请码业务专属方法 ===================================
    async def set_invite_info(self, invite_info: InviteInfoSchema):
        """存入邀请信息"""
        key = f"{self.invite_prefix}{invite_info.email}"
        await self.set(
            key,
            # model_dump_json 把 pydantic对象序列化为json字符串
            invite_info.model_dump_json(),
            ex=settings.INVITE_CODE_EXPIRE,
        )

    async def get_invite_info(self, email: str) -> InviteInfoSchema | None:
        """获取邀请信息"""
        key = f"{self.invite_prefix}{email}"
        invite_info_json = await self.get(key)
        if invite_info_json is not None:
            # model_validate_json 把json字符串反序列化并校验成pydantic对象
            invite_info = InviteInfoSchema.model_validate_json(invite_info_json)
            return invite_info
        return None

    # ================ 钉钉业务专属方法 ===================================
    async def set_ding_info(self, dingtalk_info: DingTalkTokenInfoSchema):
        key = f"{self.dingding_prefix}{dingtalk_info.user_id}"
        expire_second = (
            settings.JWT_REFRESH_TOKEN_EXPIRES - timedelta(days=1)
        ).total_seconds()
        await self.set(
            key,
            dingtalk_info.model_dump_json(),
            # 和REFRESH_TOKEN的过期时间剪一天
            ex=int(expire_second),
        )

    async def get_ding_info(self, user_id: str):
        key = f"{self.dingding_prefix}{user_id}"
        return await self.get(key)
