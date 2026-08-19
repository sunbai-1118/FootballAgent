from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic import Field

# 新闻模型类
class NewsItemBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(..., alias="categoryId", description="分类ID")
    views: int = 0
    publish_time: Optional[datetime] = Field(None, alias="publishTime", description="发布时间")

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True
    )