# 统一返回格式
from typing import Any

from pydantic import BaseModel


class Response(BaseModel):
    """统一响应格式"""

    code: int
    message: str
    data: Any = None

    @classmethod
    def success(cls, message: str = "操作成功", data: Any = None):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, message: str = "请求失败", code: int = 500):
        return cls(code=code, message=message)
