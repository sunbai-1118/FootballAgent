"""回答反馈 ORM 模型（对应 answer_feedback 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.mysql import ENUM, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AnswerFeedback(Base):
    """回答反馈表：用户对 AI 回答的 👍/👎，用于优化 Prompt/RAG/Tool"""

    __tablename__ = "answer_feedback"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="反馈ID")
    ai_chat_id: Mapped[Optional[int]] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("ai_chat.id", ondelete="SET NULL"), comment="关联的回答记录ID"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), comment="用户ID"
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(32), comment="OTel trace_id(关联日志链路)")
    score: Mapped[str] = mapped_column(
        ENUM("up", "down"), nullable=False, comment="反馈:up(👍)/down(👎)"
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, comment="反馈原因(可选)")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
