"""球队信息 ORM 模型（对应 team 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Team(Base):
    """球队信息表"""

    __tablename__ = "team"

    __table_args__ = (
        Index("uk_team_api_id", "api_id", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="球队ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="球队名")
    country: Mapped[Optional[str]] = mapped_column(String(50), comment="国家")
    league: Mapped[Optional[str]] = mapped_column(String(50), comment="所属联赛")
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), comment="队徽URL")
    api_id: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="api-football外部ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
