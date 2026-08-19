"""AI 聊天记录 ORM 模型（对应 ai_chat 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AiChat(Base):
    """AI 聊天记录表"""
    __tablename__ = "ai_chat"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="聊天记录ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True, comment="会话ID")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户消息")
    response: Mapped[str] = mapped_column(Text, nullable=False, comment="AI回复")
    agent_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Agent工具调用轨迹JSON")
    trace_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="OTel trace_id(关联反馈/日志链路)")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
