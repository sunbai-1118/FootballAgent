"""球员信息 ORM 模型（对应 player 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Player(Base):
    """球员信息表"""

    __tablename__ = "player"

    __table_args__ = (
        Index("idx_player_team", "team_id"),
        Index("uk_player_api_id", "api_id", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="球员ID")
    team_id: Mapped[Optional[int]] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("team.id", ondelete="SET NULL"), comment="所属球队"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="球员名")
    position: Mapped[Optional[str]] = mapped_column(String(50), comment="位置")
    nationality: Mapped[Optional[str]] = mapped_column(String(50), comment="国籍")
    age: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="年龄")
    photo_url: Mapped[Optional[str]] = mapped_column(String(255), comment="照片URL")
    api_id: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="api-football外部ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
