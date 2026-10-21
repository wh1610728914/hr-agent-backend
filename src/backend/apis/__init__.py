# 只做api

from fastapi import APIRouter
from .auth import router as auth_router

from .user import router as user_router
from .department import router as department_router
from .ding import router as ding_router
from .hr import router as hr_router
from .position import router as position_router
from .candidate import router as candidate_router

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(user_router)
api.include_router(department_router)
api.include_router(ding_router)
api.include_router(hr_router)
api.include_router(position_router)
api.include_router(candidate_router)
