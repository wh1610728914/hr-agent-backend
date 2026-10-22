from pyclbr import Class
from uuid import uuid4

import aiofiles
from backend.core.ocr import PaddleOcr
from backend.repository.candidate import CandidateRepo
from backend.schemas import Response
from backend.schemas.candidate import (
    ResumeParseRequest,
    ResumeParseResponse,
    ResumeResponse,
)
from backend.settings import settings
from backend.core.exceptions import BusinessException
from backend.core.pdf import WordToPdfConverter
from backend.models.user import UserModel
from backend.tasks.ocr_task import ocr_parse_resume_task
from fastapi import BackgroundTasks, File, UploadFile
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
            fp.close()

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
    candidate_repo = CandidateRepo(db)
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
