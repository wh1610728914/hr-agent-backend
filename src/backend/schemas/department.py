from pydantic import BaseModel, ConfigDict, Field


class DepartmentResponse(BaseModel):
    """部门信息"""

    id: str = Field(..., description="部门ID")
    name: str = Field(..., description="部门名称")
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)
