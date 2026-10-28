import asyncio
from pathlib import Path
from uuid import uuid4

from backend.core.cache import HRCache, OCRInfoSchema
from backend.repository.candidate import CandidateRepo
from backend.repository.position import PositionRepo
from backend.repository.user import UserRepo
from backend.schemas.candidate import (
    CandidateSchema,
    CreateCandidateRequest,
    ResumeParseRequest,
)
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema
from backend.settings import settings
from backend.core.ocr import PaddleOcr
from backend.dependencies.db import get_db
from backend.dependencies.user import get_cache_instance, get_current_user
from backend.models.user import UserModel
from backend.schemas import PageResponse, Response
from backend.services.candidate import (
    create_candidate_service,
    get_candidate_list_service,
    get_score_candidate,
    parse_resume_service,
    update_candidate_status_service,
    upload_resume_service,
)
from backend.tasks.agent import run_agent_test
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
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
    print("can", data)
    res = await create_candidate_service(data, user, db)
    return Response.success(data=res)


@router.get("/list", summary="获取候选人列表")
async def get_candidate_list(
    page: int = Query(1, description="页码"),
    size: int = Query(10, description="每页的数量"),
    keyword: str | None = Query(None, description="根据关键字查询"),
    _: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total, list = await get_candidate_list_service(page, size, keyword, db)
    print(list)
    return PageResponse(list=list, total=total)


@router.get("/ai-score/{candidate_id}", summary="获取候选人ai得分")
async def get_ai_candidate_score(
    candidate_id: str,
    _: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await get_score_candidate(db, id=candidate_id)
    return Response.success(data=res)


@router.post("/agent/test", summary="测试候选人agent")
async def agent_test(
    background_tasks: BackgroundTasks,
    _: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    candidate_repo = CandidateRepo(db)
    position_repo = PositionRepo(db)
    interview_repo = UserRepo(db)
    candidate_model = await candidate_repo.by_get_id("PWiQS3rdfASXRNbUhJAARR")
    # print("对应的候选人是", CandidateSchema.model_validate(candidate_model))
    position_model = await position_repo.get_by_id("c4YerzVnpyukj5WXH75sV2")
    interview_model = await interview_repo.check_by_id("5j3UfAnoxLVdg4RVN7n3xH")
    res = background_tasks.add_task(
        run_agent_test,
        candidate=CandidateSchema.model_validate(candidate_model),
        position=PositionSchema.model_validate(position_model),
        interview=UserSchema.model_validate(interview_model),
    )
    return Response.success(data=res)


@router.get("/update/status/{candidate_id}", summary="更新候选人状态")
async def update_candidate_status(
    candidate_id: str, val: str, db: AsyncSession = Depends(get_db)
):
    """
    candidate_id：候选人id
    val：更新的候选人状态
    """

    res = await update_candidate_status_service(candidate_id, val, db)
    return Response.success(message=res)
