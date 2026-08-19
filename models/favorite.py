"""收藏 ORM 模型（对应 favorite 表）"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

# 2.定义模型类
class Favorite(Base):
    """收藏表"""
    __tablename__ = "favorite"

    # 创建索引
    # UniqueConstraint：创建唯一约束,当前新闻只能收藏一次
    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
        Index("fk_favorite_user_id", "user_id"),
        Index("fk_favorite_news_id", "news_id")
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    news_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("news.id", ondelete="CASCADE"), nullable=False, comment="新闻ID"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="收藏时间")

    def __repr__(self) -> str:
        return f"<Favorite id={self.id}, user_id={self.user_id}, news_id={self.news_id}, created_at={self.created_at}>"
