"""用户长期记忆 ORM 模型（对应 user_memory 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class UserMemory(Base):
    """用户长期记忆：经记忆筛选层入库的用户偏好/事实，跨会话有效"""

    __tablename__ = "user_memory"

    __table_args__ = (
        Index("idx_user_memory_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="记忆ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="记忆内容(用户偏好/事实)")
    memory_type: Mapped[str] = mapped_column(
        String(20), default="preference", server_default="preference", comment="类型:preference偏好/fact事实"
    )
    importance: Mapped[int] = mapped_column(
        TINYINT(unsigned=True), default=3, server_default="3", comment="重要性1-5(超预算裁剪用)"
    )
    source_session_id: Mapped[Optional[str]] = mapped_column(String(64), comment="来源会话ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), server_onupdate=func.now(), comment="更新时间"
    )
