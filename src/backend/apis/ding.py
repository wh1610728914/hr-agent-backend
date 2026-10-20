# 钉钉涉及的接口

from urllib.parse import urlencode, urljoin

from backend.settings import settings
from backend.dependencies.db import get_db
from backend.dependencies.user import get_current_user
from backend.models.user import UserModel
from backend.schemas import Response
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dingtalk", tags=["钉钉"])


@router.get("/authorize", summary="获取登录钉钉的URL")
async def dingtalk_authorize(current_user: UserModel = Depends(get_current_user)):
    # redirect_uri 必须是公网可以访问的api
    params = {
        # 用urljoin进行拼接
        "redirect_uri": urljoin(settings.BACKEND_BASE_URL, "/dingtalk/callback"),
        "response_type": "code",
        "client_id": settings.DING_CLIENT_ID,
        "scope": "openid",
        "state": current_user.id,
        "prompt": "consent",
    }
    # urlencode 自动把params进行编码拼接
    authorize_url = f"https://login.dingtalk.com/oauth2/auth?{urlencode(params)}"
    return Response.success(data=authorize_url)


@router.get("/callback", summary="")
async def dingtalk_callback(
    state: str,
    code: str | None = None,
    authCode: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    pass
