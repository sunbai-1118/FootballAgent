"""新闻相关 ORM 模型（对应 news_category / news / related_news 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

# ==================== 模型类 ====================
# 创建新闻分类表模型类
class NewsCategory(Base):
    """新闻分类表"""
    __tablename__ = "news_category"
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(INTEGER, default=0, server_default="0", comment="排序顺序")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), server_onupdate=func.now(), comment="更新时间"
    )
    # 打印对象时能够在控制台显示对象信息
    def __repr__(self) -> str:
        return f"<NewsCategory(id={self.id}, name={self.name}, sort_order={self.sort_order})>"

# 创建新闻表模型类
class News(Base):
    """新闻表"""
    __tablename__ = "news"

    # 创建索引 ： 提升查询速度 - > 添加目录
    __table_args__ = (
        Index("idx_news_category_id", "category_id"),   # 高频查询场景
        Index("idx_publish_time", "publish_time")       # 按发布时间排序
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[Optional[str]] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("news_category.id", ondelete="RESTRICT"),
        nullable=False,
        comment="分类ID",
    )
    views: Mapped[int] = mapped_column(INTEGER(unsigned=True), default=0, server_default="0", comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="发布时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), server_onupdate=func.now(), comment="更新时间"
    )
    # 打印对象时能够在控制台显示对象信息
    def __repr__(self) -> str:
        return f"<News(id={self.id}, title={self.title}, category_id={self.category_id})>"

# 创建相关新闻关联表模型类
class RelatedNews(Base):
    """相关新闻关联表（推荐系统）"""
    __tablename__ = "related_news"
    __table_args__ = (UniqueConstraint("news_id", "related_news_id", name="news_related_unique"),)

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="关联ID")
    news_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("news.id", ondelete="CASCADE"), nullable=False, comment="新闻ID"
    )
    related_news_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("news.id", ondelete="CASCADE"), nullable=False, comment="相关新闻ID"
    )
    # 打印对象时能够在控制台显示对象信息
    def __repr__(self) -> str:
        return f"<RelatedNews(id={self.id}, news_id={self.news_id}, related_news_id={self.related_news_id})>"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")

