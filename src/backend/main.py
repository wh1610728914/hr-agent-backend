from contextlib import asynccontextmanager

from backend.schedule import shutdown_email_polling, start_email_polling

from loguru import logger
import redis.asyncio as asioRedis
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from backend.core.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    valid_exception_handler,
    excep_exception_handler,
)
from backend.settings import settings
from backend.apis import api
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache

from loguru import logger

logger.remove()
logger.add(
    "log/app.log",
    rotation="10 MB",  # 每个文件最大 10MB
    retention="7 days",  # 保留最近 7 天的日志
    compression="zip",  # 压缩旧日志为 zip 文件
    level="INFO",  # 最低记录级别
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
    enqueue=True,  # 多进程安全写入
)


# 异步上下文管理器
# @asynccontextmanager
# async def lifespan(app:FastAPI):
# """
# lifespan：名字随便起，只是约定俗成是这个
# 意思是 生命周期，这个函数的作用就是管理应用从启动到关闭的整个生命周期
# """
@asynccontextmanager
async def manage_redis(app: FastAPI):
    """
    利用FastAPI的Lifespan（生命周期）机制，完成Redis缓存后端的全局初始化与资源托管
    在应用生命周期内初始化全局 Redis 异步连接池，
    并将其挂载至 FastAPI-Cache 作为缓存后端，确保应用关闭时自动释放连接资源
    """

    redis = asioRedis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        encoding="utf-8",
        protocol=2,  # 👈 关键：强制使用 RESP2，避免发送 HELLO 命令
        # descode_response=True,
        # 让redis返回的数据自动解码为Python字符串（而不是字节）方便后续JSON序列化处理
    )
    # 截止到这里，只是创建了客户端对象，并没有真正建立TCP连接，Redis客户端通常是懒加载，第一次执行命令时才连

    redis_backend = RedisBackend(
        redis
    )  # 将上面创建的异步redis客户端包装成 fastapi-cache可以识别的后端接口

    # init 全局初始化缓存系统
    FastAPICache.init(
        redis_backend,
        # 命名空间前缀，所有生成的缓存键都会以这个开头，有助于区分不同应用的数据
        prefix="fastapi-cache",
    )

    yield
    await redis.close()


@asynccontextmanager
async def email_pool(app: FastAPI):
    """轮询查找最新邮件 candidate的agent"""
    logger.info("轮询开启中。。。。")
    bot, scheduler = await start_email_polling()

    try:

        yield
    finally:
        logger.info("轮询关闭中。。。。")
        await shutdown_email_polling(bot, scheduler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with manage_redis(app):
        async with email_pool(app):
            yield


app = FastAPI(
    # 把定义好的lifespan函数注册到fastAPI实例中
    lifespan=lifespan,
)
app.include_router(api)
# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, valid_exception_handler)
app.add_exception_handler(Exception, excep_exception_handler)

# 跨域
origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # 允许前端携带  Authorization token
)
