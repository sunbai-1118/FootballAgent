"""足球领域数据操作：球队(team)/比赛(match)缓存（按 api-football 外部ID upsert）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.match import Match
from models.team import Team


async def get_team_by_api_id(db: AsyncSession, api_id: int) -> Optional[Team]:
    result = await db.execute(select(Team).where(Team.api_id == api_id))
    return result.scalar_one_or_none()


async def upsert_team(
    db: AsyncSession,
    name: str,
    api_id: Optional[int] = None,
    country: Optional[str] = None,
    league: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> Team:
    """按 api_id 幂等写入球队（存在则补字段，否则新增）"""
    record = await get_team_by_api_id(db, api_id) if api_id else None
    if record is None:
        record = Team(name=name, api_id=api_id, country=country, league=league, logo_url=logo_url)
        db.add(record)
    else:
        if name:
            record.name = name
        if country:
            record.country = country
        if league:
            record.league = league
        if logo_url:
            record.logo_url = logo_url
    await db.commit()
    await db.refresh(record)
    return record


async def get_match_by_api_id(db: AsyncSession, api_id: int) -> Optional[Match]:
    result = await db.execute(select(Match).where(Match.api_id == api_id))
    return result.scalar_one_or_none()


async def upsert_match(
    db: AsyncSession,
    api_id: int,
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
    season: Optional[str] = None,
    round_: Optional[str] = None,
    home_team_id: Optional[int] = None,
    away_team_id: Optional[int] = None,
    match_date: Optional[datetime] = None,
    status: Optional[str] = None,
    home_score: Optional[int] = None,
    away_score: Optional[int] = None,
    venue: Optional[str] = None,
) -> Match:
    """按 api_id 幂等写入比赛（存在则补字段，否则新增）"""
    record = await get_match_by_api_id(db, api_id)
    if record is None:
        record = Match(
            api_id=api_id, home_team=home_team, away_team=away_team,
            league=league, season=season, round=round_,
            home_team_id=home_team_id, away_team_id=away_team_id,
            match_date=match_date, status=status,
            home_score=home_score, away_score=away_score, venue=venue,
        )
        db.add(record)
    else:
        record.home_team = home_team or record.home_team
        record.away_team = away_team or record.away_team
        for key, val in (
            ("league", league), ("season", season), ("round", round_),
            ("home_team_id", home_team_id), ("away_team_id", away_team_id),
            ("match_date", match_date), ("status", status),
            ("home_score", home_score), ("away_score", away_score), ("venue", venue),
        ):
            if val is not None:
                setattr(record, key, val)
    await db.commit()
    await db.refresh(record)
    return record
