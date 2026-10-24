from datetime import datetime
from typing import Optional

from backend.models.department import DepartmentModel
from backend.models.positions import EducationEnum
from backend.models.user import UserModel
from backend.schemas.department import DepartmentResponse
from backend.schemas.user import UserResponse
from pydantic import BaseModel, ConfigDict, Field


class PositionRequest(BaseModel):
    """创建职位信息"""

    title: str = Field(..., description="职位")
    description: Optional[str] = Field(None, description="职位描述")
    requirements: Optional[str] = Field(None, description="职位要求")
    min_salary: Optional[int] = Field(None, description="最低薪资")
    max_salary: Optional[int] = Field(None, description="最高薪资")
    deadline: Optional[datetime] = Field(None, description="招聘截至日期")
    recruitment_count: int = Field(1, description="招聘人数")
    # 最低学历要求
    education: EducationEnum = Field(..., description="最低学历要求")
    # 最低工作年限要求
    work_year: int = Field(0, description="最低工作年限")


class PositionSchema(PositionRequest):
    pass


class PositionResponse(PositionRequest):
    """职位信息返回"""

    id: str = Field(..., description="职位ID")
    creator: UserResponse = Field(..., description="职位创建者")
    department: DepartmentResponse = Field(..., description="所属部门")
    model_config = ConfigDict(from_attributes=True)
