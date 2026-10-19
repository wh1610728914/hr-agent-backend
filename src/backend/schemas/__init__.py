# 统一返回格式
from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict


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


T = TypeVar("T")  # 声明一个类型变量（占位符）


class PageResponse(
    BaseModel,
    # 我这个 PageResponse 类是一个泛型类，我内部会用到名叫 T 的占位符”。
    Generic[T],
):
    """分页de统一响应格式"""

    list: List[T] = []
    total: int = 0
