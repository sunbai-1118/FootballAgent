"""比赛信息 ORM 模型（对应 match 表）

注意：MATCH 是 MySQL 保留字（MATCH...AGAINST 全文检索），
用 quoted_name 强制 SQLAlchemy 生成的 SQL 加反引号。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Index, quoted_name
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Match(Base):
    """比赛信息表"""

    __tablename__ = quoted_name("match", True)

    __table_args__ = (
        Index("idx_match_home", "home_team_id"),
        Index("idx_match_away", "away_team_id"),
        Index("uk_match_api_id", "api_id", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="比赛ID")
    league: Mapped[Optional[str]] = mapped_column(String(50), comment="联赛")
    season: Mapped[Optional[str]] = mapped_column(String(10), comment="赛季")
    round: Mapped[Optional[str]] = mapped_column(String(50), comment="轮次/阶段")
    home_team_id: Mapped[Optional[int]] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("team.id", ondelete="SET NULL"), comment="主队ID"
    )
    away_team_id: Mapped[Optional[int]] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("team.id", ondelete="SET NULL"), comment="客队ID"
    )
    home_team: Mapped[str] = mapped_column(String(100), nullable=False, comment="主队名(冗余便于展示)")
    away_team: Mapped[str] = mapped_column(String(100), nullable=False, comment="客队名(冗余便于展示)")
    match_date: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="比赛时间")
    status: Mapped[Optional[str]] = mapped_column(String(20), comment="状态:scheduled/live/finished")
    home_score: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="主队比分")
    away_score: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="客队比分")
    venue: Mapped[Optional[str]] = mapped_column(String(100), comment="场地")
    api_id: Mapped[Optional[int]] = mapped_column(INTEGER(unsigned=True), comment="api-football fixture外部ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
