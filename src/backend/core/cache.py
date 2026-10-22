# 缓存


from datetime import timedelta
from typing import Any, Literal

from backend.schemas.agents import ResumeAgentsResponse
from backend.schemas.cache import (
    DingTalkTokenInfoSchema,
    InviteInfoSchema,
    OCRInfoSchema,
)
from backend.settings import settings
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache
from pydantic import BaseModel, EmailStr

# redis缓存


# HRCache
class HRCache:
    """管理HR邀请信息的缓存"""

    invite_prefix = "invite:"  # key前缀，用于命名空间隔离
    dingding_prefix = "dings:"
    ocr_prefix = "orc:"

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
    async def set_invite_code(self, invite_info: InviteInfoSchema):
        print("邀请码", invite_info)
        """设置邀请码"""
        key = f"{self.invite_prefix}{invite_info.email}"
        expire_second = 60 * 60 * 12 * 30  # 一个月过期
        await self.set(key, invite_info.model_dump_json(), ex=int(expire_second))

    async def get_invite_code(self, email: str):
        """获取邀请码"""
        key = f"{self.invite_prefix}{email}"
        result = await self.get(key)
        if result is not None:
            return InviteInfoSchema.model_validate_json(result)
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

    # ================ ocr专属方法 ===================================
    async def set_ocr_info(self, ocr_info: OCRInfoSchema):
        key = f"{self.ocr_prefix}{ocr_info.task_id}"
        expire_second = 60 * 60 * 1
        # redis只能接收字符串
        await self.set(key, ocr_info.model_dump_json(), ex=int(expire_second))

    async def get_ocr_info(self, task_id: str):
        """获取ocr内容"""
        key = f"{self.ocr_prefix}{task_id}"
        result = await self.get(key)
        if result is not None:  # 拿到的json，json字符串变成对象
            return OCRInfoSchema.model_validate_json(result)
        return None
