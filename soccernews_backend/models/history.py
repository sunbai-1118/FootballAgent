"""浏览历史 ORM 模型（对应 history 表）"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class History(Base):
    """浏览历史表"""
    __tablename__ = "history"

    # 创建索引与唯一约束（同一用户同一新闻只保留一条浏览记录）
    __table_args__ = (
        # 创建索引
        Index("idx_history_user_id", "user_id"),
        Index("idx_history_news_id", "news_id"),
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="历史ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    news_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("news.id", ondelete="CASCADE"), nullable=False, comment="新闻ID"
    )
    view_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="浏览时间")

    def __repr__(self) -> str:
        return f"<History id={self.id}, user_id={self.user_id}, news_id={self.news_id}, view_time={self.view_time}>"
