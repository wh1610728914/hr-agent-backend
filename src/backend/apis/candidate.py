from backend.dependencies.db import get_db
from backend.dependencies.user import get_current_user
from backend.models.user import UserModel
from backend.schemas import Response
from backend.services.candidate import upload_resume_service
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/candidate", tags=["候选人相关"])


@router.post("/resume/upload", summary="上传简历")
async def upload_resume(
    file: UploadFile = File(...),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await upload_resume_service(file, user, db)
    print(res)
    return Response.success(data=res)
