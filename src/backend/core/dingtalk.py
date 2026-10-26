# 管理钉钉的api
from urllib.parse import urljoin

from backend.core.exceptions import BusinessException
from backend.settings import settings
import httpx


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
