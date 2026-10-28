# 用来做定时任务调度的 uv add schedule
# 那我需要每隔15s 去邮箱看看有没有收到新邮件。然后再调用llm回复候选人


from backend.agents.candidate import CandidateProcessAgent
from backend.core.cache import HRCache
from backend.core.emailBot.bot import EmailBot
from backend.dependencies.user import get_cache_instance

from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema
from backend.settings import settings
from backend.core.emailBot.settings import EmailBotSetting
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from langchain.messages import HumanMessage
from loguru import logger

scheduler = AsyncIOScheduler()


async def pool_and_process_emails(bot: EmailBot, state: dict):
    """轮询处理这个邮件

    读取 last_uid（上次处理到的邮件 UID）
    拉取 last_uid 之后的新邮件
    逐封交给 CandidateProcessAgent 处理
    更新并持久化 last_uid 到 HRCache
    """
    # 1.读取 last_uid（上次处理到的邮件 UID）

    cache: HRCache = get_cache_instance()
    pre_last_uid = state["last_uid"]

    # 2.拉取 last_uid 之后的新邮件
    new_emails = await bot.fetch_since_uid(pre_last_uid)
    if not new_emails:
        return
    new_emails.sort(key=lambda e: int(e.uid))
    for mail in new_emails:
        if mail.from_.address.lower() == bot.settings.email.lower():
            continue
        logger.info(f"收到新邮件，来自: {mail.from_.address}, 主题: {mail.subject}")
        try:
            async with CandidateProcessAgent() as agent:
                if mail.from_.address.lower() == bot.settings.email.lower():
                    continue
                thread_id = mail.from_.address
                await agent.ainvoke(
                    messages=[
                        HumanMessage(content=f"收到邮件内容：{mail.text or mail.html}")
                    ],
                    thread_id=thread_id,
                )

                state["last_uid"] = max(state["last_uid"], int(mail.uid))
                try:
                    cache = HRCache()
                    await cache.set_email_last_uid(state["last_uid"])
                except Exception as e:
                    logger.exception(f"从redis查找last_uid失败，错误是：{e}")
        except Exception as e:
            logger.exception(f"处理邮件UID={mail.uid}失败，错误是{e}")
            return f"轮询邮件失败，错误是{e}"


async def start_email_polling():
    """开启轮询"""
    email_setting = EmailBotSetting(
        imap_host=settings.IMAP_HOST,
        smtp_host=settings.SMTP_HOST,
        email=settings.EMAIL_USERNAME,
        password=settings.EMAIL_PASSWORD,
    )
    bot = EmailBot(email_setting)
    cache: HRCache = get_cache_instance()
    last_uid = await cache.get_email_last_uid()
    if last_uid is None:
        last_uid = await bot.get_max_uid() or 0
        await cache.set_email_last_uid(last_uid)
    state: dict = {"last_uid": last_uid}
    await bot.connect()
    scheduler.add_job(
        pool_and_process_emails,
        "interval",
        seconds=15,
        args=[bot, state],
        max_instances=1,
    )
    scheduler.start()
    logger.info("正在轮询中。。。。。。")
    return bot, scheduler


async def shutdown_email_polling(bot: EmailBot, scheduler: AsyncIOScheduler):
    """关闭轮询与邮件连接"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    finally:
        await bot.close()
        logger.info("邮件轮询已停止")
