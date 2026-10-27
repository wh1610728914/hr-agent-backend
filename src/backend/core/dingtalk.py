# 管理钉钉的api
import asyncio
from typing import Awaitable, Callable
from urllib.parse import urljoin

from backend.core.cache import HRCache
from backend.core.exceptions import BusinessException
from backend.dependencies.user import get_cache_instance
from backend.schemas.cache import DingTalkTokenInfoSchema
from backend.settings import settings
import httpx
from loguru import logger


class DingTalkApi:
    dingtalk_api_base_url: str = "https://api.dingtalk.com"

    @classmethod
    def build_access_token_url(cls):
        """获取token路径"""
        return urljoin(cls.dingtalk_api_base_url, "/v1.0/oauth2/userAccessToken")

    @classmethod
    def build_my_info_url(cls):
        """获取用户信息路径"""
        return urljoin(cls.dingtalk_api_base_url, "/v1.0/contact/users/me")

    @classmethod
    def get_calendar_url(cls, unionID, calendarId="primary"):
        return urljoin(
            cls.dingtalk_api_base_url,
            f"/calendar/users/{unionID}/calendars/{calendarId}/events",
        )

    @classmethod
    def create_calendar_url(cls, unionID, calendarId="primary"):
        return cls.get_calendar_url(unionID, calendarId)

    async def refresh_access_token(self, refresh_token: str):
        """刷新access_token"""
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                url=DingTalkApi.build_access_token_url(),
                json={
                    "clientId": settings.DING_CLIENT_ID,
                    "clientSecret": settings.DING_CLIENT_SECRET,
                    "refreshToken": refresh_token,
                    "grantType": "refresh_token",
                },
            )
            if token_resp.status_code != 200:
                raise BusinessException(message=f"Token刷新失败!{token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data["accessToken"]
            refresh_token = token_data["refreshToken"]
            res = {"refresh_token": refresh_token, "access_token": access_token}
            return res


class DingTalkHttp:
    # 同一个 user 的刷新串行化，避免并发 401 时 refresh_token 被用两次
    _refresh_locks: dict[str, asyncio.Lock] = {}

    def _get_refresh_lock(self, user_id: str) -> asyncio.Lock:
        lock = self._refresh_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._refresh_locks[user_id] = lock
        return lock

    async def get_ding_token(self, user_id: str) -> DingTalkTokenInfoSchema | None:
        """只取 token，不刷新。没有/解析失败都返回 None。"""
        cache: HRCache = get_cache_instance()
        raw = await cache.get_ding_info(user_id=user_id)
        if not raw:
            return None
        try:
            return DingTalkTokenInfoSchema.model_validate_json(raw)
        except Exception as e:
            logger.warning(f"解析钉钉token失败 user_id={user_id}: {e}")
            return None

    async def _refresh_and_save(
        self, user_id: str, refresh_token: str
    ) -> DingTalkTokenInfoSchema | None:
        """刷新 token 并回写缓存。失败返回 None。调用方需持有该 user 的锁。"""
        new_token = await DingTalkApi.refresh_access_token(refresh_token)
        if not new_token:
            return None
        token = DingTalkTokenInfoSchema(
            access_token=new_token["access_token"],
            refresh_token=new_token["refresh_token"],
            user_id=user_id,
        )
        cache: HRCache = get_cache_instance()
        await cache.set_ding_info(token)
        return token

    async def request_with_ding_token(
        self,
        user_id: str,
        make_request: Callable[[str], Awaitable[httpx.Response]],
    ) -> httpx.Response:
        """
        用 user_id 对应的钉钉 token 发请求。
        - token 不存在：抛 BusinessException
        - 401：加锁后刷新一次，回写缓存，重试一次；刷新失败抛 BusinessException
        - 重试后仍 401：抛 BusinessException
        其他状态码原样返回，由调用方判断。
        """
        token = await self.get_ding_token(user_id)
        if not token:
            raise BusinessException(f"面试官{user_id}的钉钉token不存在，请重新授权")

        resp = await make_request(token.access_token)
        if resp.status_code != 401:
            return resp

        # 401：加锁刷新，锁内再查一次缓存，可能别的请求已经刷过了
        lock = self._get_refresh_lock(user_id)
        async with lock:
            latest = await self.get_ding_token(user_id)
            # 缓存里的 access_token 已经不是刚才那个，说明别人刷新过了，直接用新的重试
            if latest and latest.access_token != token.access_token:
                resp = await make_request(latest.access_token)
                if resp.status_code == 401:
                    raise BusinessException(
                        f"面试官{user_id}的钉钉token刷新后仍无效，请重新授权"
                    )
                return resp

            refreshed = await self._refresh_and_save(user_id, token.refresh_token)
            if not refreshed:
                raise BusinessException(
                    f"面试官{user_id}的钉钉token已过期且刷新失败，请重新授权"
                )

            resp = await make_request(refreshed.access_token)
            if resp.status_code == 401:
                raise BusinessException(
                    f"面试官{user_id}的钉钉token刷新后仍无效，请重新授权"
                )
            return resp
