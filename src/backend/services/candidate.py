from datetime import datetime, timedelta

from uuid import uuid4
from xmlrpc.client import INTERNAL_ERROR

import aiofiles


from backend.models.candidate import CandidateStatusEnum
from backend.models.interview import InterviewResultEnum
from backend.repository.candidate import CandidateRepo, ResumeRepo
from backend.repository.interview import Interview
from backend.schemas.candidate import (
    CandidateAIScopeSchema,
    CandidateSchema,
    CandidateUpdateRequest,
    CreateCandidateRequest,
    ResumeParseRequest,
    ResumeParseResponse,
    ResumeResponse,
)


from backend.settings import settings
from backend.core.exceptions import BusinessException
from backend.core.pdf import WordToPdfConverter
from backend.models.user import UserModel
from backend.tasks.ocr_task import ocr_parse_resume_task
from fastapi import BackgroundTasks, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path


async def upload_resume_service(file: UploadFile, user: UserModel, db: AsyncSession):
    """上传简历"""
    # 1.只能传图片，word，pdf
    allow_file_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/jpg",
    ]

    if file.content_type not in allow_file_types:
        raise BusinessException(message="不被允许上传的文件后缀")

    # 2.把简历存到文件夹中
    file_ex = Path(file.filename).suffix.lower()  # 拿到后缀名
    new_file_name = f"{uuid4()}{file_ex}"
    save_path = Path(settings.RESUME_DIR) / new_file_name
    async with aiofiles.open(save_path, "wb") as fp:
        try:
            """把文件存入"""
            chunk = await file.read(1024)
            while chunk:
                await fp.write(chunk)
                chunk = await file.read(1024)
        finally:
            await fp.close()

    # 3.把word变成pdf
    transform_types = [".docx", ".doc"]
    if file_ex in transform_types:
        pdf_path = save_path.with_suffix(".pdf")  # 后缀名变成pdf
        file_converter = WordToPdfConverter(
            word_path=save_path, output_pdf_path=pdf_path
        )
        try:
            await file_converter.convert()
            save_path = pdf_path
        except Exception as e:
            logger.error(f"word转pdf失败：{e}")

    # 4.存数据库
    candidate_repo = ResumeRepo(db)
    res = await candidate_repo.upload_resume(file_path=save_path, uploader_id=user.id)

    return ResumeResponse.model_validate(res)


async def parse_resume_service(
    data: ResumeParseRequest,
    task_id: str,
    background_tasks: BackgroundTasks,
):
    """解析简历"""
    background_tasks.add_task(
        ocr_parse_resume_task, resume_id=data.resume_id, task_id=task_id
    )
    return ResumeParseResponse.model_validate({"task_id": task_id})


async def create_candidate_service(
    data: CreateCandidateRequest, user: UserModel, db: AsyncSession
):
    """创建候选人"""

    candidate_repo = CandidateRepo(db)
    # pydantic 转为字典
    data_dict = data.model_dump()
    candidate_info = await candidate_repo.by_get_id(data.email)
    if candidate_info:
        raise BusinessException(message="不可重复添加候选人")
    res = await candidate_repo.create_candidate(user, data_dict)
    return CandidateSchema.model_validate(res)


async def get_candidate_list_service(page, size, keyword, db: AsyncSession):
    """获取候选人列表"""
    candidate_repo = CandidateRepo(db)
    total, list = await candidate_repo.get_candidate_list(page, size, keyword)
    print(total)
    print("*" * 30)
    res = [CandidateSchema.model_validate(li) for li in list]
    # print("结果结果", res)
    return total, [CandidateSchema.model_validate(li) for li in list]


async def get_score_candidate(db: AsyncSession, id):
    """获取候选人ai得分情况"""
    candidate_repo = CandidateRepo(db)
    res = candidate_repo.get_score_candidate(id)
    if not res:
        raise BusinessException(message="该候选人暂时没有ai得分情况，请稍后查询")
    return CandidateAIScopeSchema.model_validate(res)


CANDIDATE_STATUS = [
    CandidateStatusEnum.APPLICATION,  # 已投递
    CandidateStatusEnum.AI_FILTER_FAILED,  # AI筛选失败
    CandidateStatusEnum.AI_FILTER_PASSED,  # AI筛选成功
    CandidateStatusEnum.INTERVIEW_PASSED,  # 面试通过
    CandidateStatusEnum.INTERVIEW_REJECTED,  # 面试未通过
    CandidateStatusEnum.HIRED,  # 已入职
    CandidateStatusEnum.REJECTED,  # 已拒绝
    CandidateStatusEnum.REFUSED_INTERVIEW,  # 拒绝面试
]


async def update_candidate_status_service(
    db: AsyncSession, id: str, restInfo: CandidateUpdateRequest
):
    """更改候选人状态"""
    candidate_repo = CandidateRepo(db)
    candidate_info: CandidateSchema = await candidate_repo.by_get_id(id)
    if not candidate_info:
        raise BusinessException(message="无该候选人信息")

    # 更改状态只能从前往后，如果该面试者状态是被拒绝，那就不能变为待面试
    current_idx = CANDIDATE_STATUS.index(candidate_info.status)
    target_idx = CANDIDATE_STATUS.index(restInfo.status)
    if target_idx < current_idx:
        raise BusinessException(message="只能选择当前状态之后的状态")
    interview_repo = Interview(db)
    if restInfo.status == CandidateStatusEnum.WAITING_FOR_INTERVIEW:
        if not restInfo.interview_time:
            raise BusinessException(message="请选择面试时间")
        try:
            await interview_repo.create_interview_repo(
                {
                    "scheduled_time": restInfo.interview_time,
                    "result": InterviewResultEnum.PENDING,
                    "candidate_id": id,
                    "interviewer_id": candidate_info.creator.id,
                }
            )
        except Exception as e:
            logger.exception(f"创建面试失败，错误是：{e}")
            return f"创建面试失败，错误是：{e}"

    elif restInfo.status in (
        CandidateStatusEnum.INTERVIEW_PASSED,  # 面试通过
        CandidateStatusEnum.INTERVIEW_REJECTED,  # 面试未通过
        CandidateStatusEnum.HIRED,  # 已入职
        CandidateStatusEnum.REJECTED,  # 已拒绝
        CandidateStatusEnum.REFUSED_INTERVIEW,  # 拒绝面试
    ):

        interview = await interview_repo.get_interview_repo(
            candidate_id=candidate_info.id
        )

        if not interview:
            raise BusinessException(message="面试记录不存在")
        data = {"id": interview.id}
        if restInfo.status == CandidateStatusEnum.INTERVIEW_REJECTED:
            # 面试未通过，要写未通过原因的
            data["reason"] = restInfo.rejection_reason
            data["status"] = InterviewResultEnum.FAILED
        else:
            data["status"] = (
                InterviewResultEnum.PASSED
                if restInfo.status
                in (CandidateStatusEnum.INTERVIEW_PASSED, CandidateStatusEnum.HIRED)
                else InterviewResultEnum.FAILED
            )
        await interview_repo.update_interview_status_repo(data)

    try:
        # 更改候选人status状态
        res = await candidate_repo.update_candidate_status(
            candidate_info, restInfo.status
        )
        return CandidateSchema.model_validate(res)
    except Exception as e:
        logger.exception(f"更改候选人状态失败,错误是{e}")


async def get_7_candidate_list_service(db: AsyncSession):
    """获取7天内的候选人"""
    candidate_repo = CandidateRepo(db)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=6)

    rows = await candidate_repo.get_7_candidate_list(
        db, start_time=start_time, end_time=end_time
    )

    print("候选人", rows)
    day_counts = {day: count for day, count in rows}
    # rows只返回有数据的天数，下面要把没数据的也拼出来
    results = []
    for x in range(7):
        day_x = (start_time + timedelta(days=x)).date()
        results.append({"days": day_x.isoformat(), "count": day_counts.get(day_x, 0)})
    return results
    # return [CandidateSchema.model_validate(item) for item in items]
