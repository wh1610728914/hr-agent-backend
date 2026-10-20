# 钉钉涉及的接口

from http import client
from urllib.parse import urlencode, urljoin

from backend.core.cache import DingTalkTokenInfoSchema, HRCache
from backend.core.dingtalk import DingTalkApi
from backend.core.exceptions import BusinessException
from backend.repository.user import UserRepo
from backend.services.ding import getDingInfoService
from backend.settings import settings
from backend.dependencies.db import get_db
from backend.dependencies.user import get_cache_instance, get_current_user
from backend.models.user import UserModel
from backend.schemas import Response
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

# 因为python不支持html，所以用jinjia2
from fastapi.templating import Jinja2Templates

jinja2Engine = Jinja2Templates(
    # 告诉引擎，html放到templates里面 （根目录下的）
    directory="templates"
)

router = APIRouter(prefix="/dingtalk", tags=["钉钉"])


@router.get("/authorize", summary="获取登录钉钉的URL")
async def dingtalk_authorize(current_user: UserModel = Depends(get_current_user)):
    # redirect_uri 必须是公网可以访问的api
    params = {
        # 用urljoin进行拼接
        "redirect_uri": urljoin(settings.BACKEND_BASE_URL, "/api/dingtalk/callback"),
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
    state: str,  # 就是dingtalk_authorize的state
    code: str | None = None,
    authCode: str | None = None,
    db: AsyncSession = Depends(get_db),
    cache: HRCache = Depends(get_cache_instance),
):
    """获取token"""

    async with httpx.AsyncClient() as client:
        user_id = state
        # 1.获取token,需要httpx
        token_resp = await client.post(
            url=DingTalkApi.build_access_token_url(),
            json={
                "clientId": settings.DING_CLIENT_ID,
                "clientSecret": settings.DING_CLIENT_SECRET,
                "code": authCode,
                "grantType": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise BusinessException(code=500, message="钉钉token获取失败")
        token_data = token_resp.json()
        access_token = token_data["accessToken"]
        refresh_token = token_data["refreshToken"]
        await cache.set_ding_info(
            DingTalkTokenInfoSchema(
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user_id,
            )
        )
        # 利用token获取用户信息
        my_info = await client.get(
            url=DingTalkApi.build_my_info_url(),
            headers={"x-acs-dingtalk-access-token": access_token},
        )
        if my_info.status_code != 200:
            raise BusinessException(message="钉钉用户获取失败")
        my_data = my_info.json()
        nick = my_data["nick"]
        mobile = my_data["mobile"]
        open_id = my_data["openId"]
        union_id = my_data["unionId"]

        # 把钉钉获取的用户信息存到数据库
        async with db.begin():
            user_repo = UserRepo(db)
            res = await user_repo.set_dingding_user(
                user_id=user_id,
                dingding_user_data={
                    "nick": nick,
                    "mobile": mobile,
                    "open_id": open_id,
                    "union_id": union_id,
                },
            )
            print(res)
        # 成功后，要跳转成功的页面
        return RedirectResponse(f"/api/dingtalk/success/page?nick={nick}")


@router.get("/success/page", summary="成功后的操作")
async def dingtalk_success(nick: str, request: Request):
    return jinja2Engine.TemplateResponse(
        "ding.html", {"username": nick, "request": request}
    )


@router.get("/info", summary="获取钉钉账号信息")
async def get_ding_info(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await getDingInfoService(current_user.id, db)
    return Response.success(data=res)
