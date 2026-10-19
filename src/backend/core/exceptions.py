# 新增多个异常处理 == 统一 ===

from backend.schemas import Response

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BusinessException(Exception):
    """自定义的业务异常"""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message


async def business_exception_handler(request: Request, exc: BusinessException):
    """拦截所有项目抛出的BusinessException异常,
    把它优雅的包装成一个统一的JSON格式返回给前端"""
    return JSONResponse(
        status_code=200,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException的统一响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(code=exc.status_code, message=exc.detail).model_dump(),
    )


async def valid_exception_handler(request: Request, exc: RequestValidationError):
    """
    pydantic抛出的异常,请求参数校验异常
    """
    error_msg = exc.errors()[0]["msg"]
    return JSONResponse(
        # 422 是fastapi默认的参数校验错误码
        status_code=422,
        content=Response.error(code=422, message=f"参数错误:{error_msg}").model_dump(),
    )


async def excep_exception_handler(request: Request, exc: Exception):
    """兜底的异常"""
    return JSONResponse(
        status_code=500,
        content=Response.error(
            code=500, message="服务器内部错误，请稍后再试"
        ).model_dump(),
    )
