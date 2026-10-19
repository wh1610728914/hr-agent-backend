# 只做api

from fastapi import APIRouter
from .auth import router as auth_router

from .user import router as user_router

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(user_router)
