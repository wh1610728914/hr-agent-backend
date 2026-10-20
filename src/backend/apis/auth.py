from backend.core.cache import HRCache
from backend.dependencies.db import get_db
from backend.dependencies.token import get_auth_handler
from backend.dependencies.user import get_cache_instance
from backend.schemas.auth import LoginRequest, RegisterRequest
from backend.services.auth import loginEmailService, registerService
from backend.core.token import AuthHandler
from backend.schemas import Response
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    authToken: AuthHandler = Depends(get_auth_handler),
):
    """登录"""
    res = await loginEmailService(data, db, authToken)
    return Response.success(data=res)


@router.post("/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    cache: HRCache = Depends(get_cache_instance),
):
    """注册"""
    res = await registerService(data, db, cache)
    return Response.success(data=res)
