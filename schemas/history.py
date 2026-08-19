"""浏览历史模块数据验证模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import NewsItemBase


class HistoryAdd(BaseModel):
    """添加浏览记录请求"""
    newsId: int = Field(..., description="新闻ID")


# class HistoryItem(BaseModel):
#     """浏览历史列表项（字段与接口文档保持一致）"""
#     id: int
#     title: str
#     description: str = ""
#     image: str = ""
#     author: str = ""
#     publishTime: Optional[datetime] = None
#     categoryId: int
#     views: int = 0
#     viewTime: Optional[datetime] = None


class HistoryNewsItem(NewsItemBase):
    """浏览历史列表项：新闻信息 + 历史记录ID + 浏览时间"""
    history_id: Optional[int] = Field(None, alias="historyId", description="历史记录ID")
    view_time: Optional[datetime] = Field(None, alias="viewTime", description="浏览时间")


class HistoryListData(BaseModel):
    """浏览历史返回（add 返回单条 id/viewTime，列表字段带默认值可省略）"""
    id: Optional[int] = None
    view_time: Optional[datetime] = Field(None, alias="viewTime", description="浏览时间")
    list: List[HistoryNewsItem] = Field(default_factory=list, description="新闻列表")
    total: int = Field(0, description="总条数")
    has_more: bool = Field(False, alias="hasMore", description="是否有更多")

    model_config = ConfigDict(populate_by_name=True)
