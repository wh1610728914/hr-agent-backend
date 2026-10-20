from typing import List

from pydantic import BaseModel, Field


class AssignDepartmentRequest(BaseModel):
    """给hr指定分配的部门 请求"""

    hr_id: str = Field(..., description="HR的id")
    department_ids: List[str] = Field(..., description="hr负责的部门的ID列表")
