"""会话短期记忆 ORM 模型（对应 session_memory 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class SessionMemory(Base):
    """会话短期记忆：三层结构中的 summary（滚动摘要）+ key_facts（结构化事实 JSON）。

    recent_messages 不在此表重复存储，直接查 ai_chat 表最近 N 轮（N 由 token 预算决定）。
    """

    __tablename__ = "session_memory"

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uk_session_memory"),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话ID")
    summary: Mapped[Optional[str]] = mapped_column(Text, comment="滚动摘要(早期轮次，自然语言)")
    key_facts: Mapped[Optional[str]] = mapped_column(Text, comment="结构化关键事实JSON")
    summarized_upto: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), default=0, server_default="0", comment="已折叠进摘要/关键事实的轮次数(从最老计)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), server_onupdate=func.now(), comment="更新时间"
    )
