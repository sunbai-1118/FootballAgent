"""新闻模块数据验证模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CategoryItem(BaseModel):
    """新闻分类"""
    id: int
    name: str
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NewsItem(BaseModel):
    """新闻列表项"""
    id: int
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    category_id: int
    views: int = 0
    publish_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NewsListData(BaseModel):
    """新闻列表返回"""
    list: List[NewsItem]
    total: int
    hasMore: bool


class RelatedNewsItem(BaseModel):
    """相关新闻"""
    id: int
    title: str
    image: Optional[str] = None
    publish_time: Optional[datetime] = None


class NewsDetail(BaseModel):
    """新闻详情返回（字段与接口文档保持一致）"""
    id: int
    title: str
    content: str
    image: Optional[str] = None
    author: Optional[str] = None
    publishTime: Optional[datetime] = None
    categoryId: int
    views: int
    relatedNews: List[RelatedNewsItem] = Field(default_factory=list)
