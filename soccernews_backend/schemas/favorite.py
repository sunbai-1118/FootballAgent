"""收藏模块数据验证模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict

from schemas.base import NewsItemBase


# 2.定义pydantic模型类

class FavoriteAddRequest(BaseModel):
    """添加收藏请求"""
    news_id: int = Field(..., alias="newsId",description="新闻ID")

class FavoriteCheckResponse(BaseModel):
    is_favorite:bool = Field(...,alias="isFavorite", description="是否已收藏")

# 收藏新闻模型类
class FavoriteNewsItemResponse(NewsItemBase):
    favorite_id: int = Field(..., alias="favoriteId", description="收藏ID")
    favorite_time: datetime = Field(..., alias="favoriteTime", description="收藏时间")

    # 配置模型属性
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# 收藏列表接口响应模型类
class FavoriteListData(BaseModel):
    list: List[FavoriteNewsItemResponse]
    total: int
    has_more: bool = Field(...,alias="hasMore", description="是否还有更多")
    # 配置模型属性
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)




