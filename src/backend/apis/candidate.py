import asyncio
from pathlib import Path
from uuid import uuid4

from backend.core.cache import HRCache, OCRInfoSchema
from backend.schemas.candidate import CreateCandidateRequest, ResumeParseRequest
from backend.settings import settings
from backend.core.ocr import PaddleOcr
from backend.dependencies.db import get_db
from backend.dependencies.user import get_cache_instance, get_current_user
from backend.models.user import UserModel
from backend.schemas import Response
from backend.services.candidate import (
    create_candidate_service,
    parse_resume_service,
    upload_resume_service,
)
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/candidate", tags=["候选人相关"])


@router.post("/resume/upload", summary="上传简历", response_model=Response)
async def upload_resume(
    file: UploadFile = File(...),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await upload_resume_service(file, user, db)
    return Response.success(data=res)


# 用户发起了一个简历识别的请求：
# 创建了一个后台任务
# 1.把任务id返回给前端
# 2.前端拿到对应的任务id ，获取任务的执行结果，当执行结果是success，就返回解析后的数据，给前端
@router.post("/resume/parse", summary="创建简历识别任务状态", response_model=Response)
async def parse_resume(
    data: ResumeParseRequest,
    background_tasks: BackgroundTasks,
    _: UserModel = Depends(get_current_user),
):
    # 拿到简历id，可以获取对应的简历信息
    task_id = str(uuid4())
    res = await parse_resume_service(data, task_id, background_tasks)
    return Response.success(data=res)


@router.get(
    "/resume/parse/{task_id}",
    summary="根据task_id获取任务解析内容",
    response_model=Response,
)
async def get_parse_resume(
    task_id: str,
    cache: HRCache = Depends(get_cache_instance),
    _: UserModel = Depends(get_current_user),
):
    # res是pydantic对象
    res: OCRInfoSchema = await cache.get_ocr_info(task_id)
    if res is None:
        await asyncio.sleep(2)
    return Response.success(data=res)


@router.get("/resume/ocr/test", summary="ocr测试")
async def ocr(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 简历路径写死的
    file_path = Path(settings.RESUME_DIR) / "e598b9ec-8622-4fd6-bb11-546f150f1237.pdf"
    ocr = PaddleOcr()
    # 1
    job_id = await ocr.create_job(str(file_path))
    # 2
    jsonl_url = await ocr.poll_for_state(job_id)
    if jsonl_url:
        # 3
        res = await ocr.fetch_parsed_contents(jsonl_url)
        print(res)
        return Response.success(data=res)


@router.post("/create", summary="添加候选人")
async def create_candidate(
    data: CreateCandidateRequest,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info("参数", data)
    res = await create_candidate_service(data, user, db)
    return Response.success(data=res)
