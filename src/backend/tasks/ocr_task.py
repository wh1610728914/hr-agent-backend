from backend.agents.resume import extract_candidate_info
from backend.core.cache import HRCache, OCRInfoSchema
from backend.core.ocr import PaddleOcr
from backend.db.database import SessionLocal
from backend.dependencies.user import get_cache_instance
from backend.repository.candidate import ResumeRepo
from backend.schemas.agents import ResumeAgentsResponse
from loguru import logger


async def ocr_parse_resume_task(resume_id: str, task_id: str):
    """简历解析任务"""
    async with SessionLocal() as db:
        candidate_repo = ResumeRepo(db)
        res = await candidate_repo.by_get_id(resume_id)
        # print("对应的简历", res)
        file_path = res.file_path

        # 存redis
        cache = get_cache_instance()
        await cache.set_ocr_info(OCRInfoSchema(task_id=task_id, status="running"))
        ocr = PaddleOcr()
        try:
            job_id = await ocr.create_job(str(file_path))
            jsonl_url = await ocr.poll_for_state(job_id)
            contents = await ocr.fetch_parsed_contents(jsonl_url)
            # 需要把content放到大模型里面，让大模型去识别其中的内容，比如姓名等
            content = "\n\n".join(contents)

            candidate_info: ResumeAgentsResponse = await extract_candidate_info(content)
            logger.info("返回的是", candidate_info)
            info = OCRInfoSchema(task_id=task_id, status="done", res=candidate_info)
        except Exception as e:
            info = OCRInfoSchema(task_id=task_id, status="failed", error=str(e))

        await cache.set_ocr_info(info)
        # res = {"content": candidate_info}
        # await cache.set_ocr_info(
        #     OCRInfoSchema(task_id=task_id, status="done", res=candidate_info)
        # )
        # except Exception as e:
        #     await cache.set_ocr_info(
        #         OCRInfoSchema(task_id=task_id, status="failed", error=str(e))
        #     )
