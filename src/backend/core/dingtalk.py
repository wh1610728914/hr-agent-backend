# 管理钉钉的api
from urllib.parse import urljoin


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
