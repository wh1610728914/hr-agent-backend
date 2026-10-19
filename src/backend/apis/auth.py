from backend.dependencies.db import get_db
from backend.dependencies.token import get_auth_handler
from backend.schemas.auth import LoginRequest
from backend.services.auth import loginEmailService
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
