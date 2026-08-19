"""足球实时数据工具：api-football（比赛结果 / 赛程 / 排名 / 球队 / 球员）

代替 web_search 处理比赛类实时信息。拉取数据时尽力缓存球队/比赛到本地表（team/match）。
"""
import logging
from datetime import datetime, timedelta

from langchain_core.tools import BaseTool, tool

from agents.observability import log_tool_call
from config.db_conf import AsyncSessionLocal
from config.football_conf import (
    API_FOOTBALL_BASE,
    API_FOOTBALL_KEY,
    API_FOOTBALL_SEASON,
    API_FOOTBALL_TIMEOUT,
    LEAGUE_IDS,
)
from crud import football as football_crud

logger = logging.getLogger(__name__)

_RESULT_WORDS = {"result", "结果", "比分", "昨天", "前场", "上一场", "战报"}
_SCHEDULE_WORDS = {"schedule", "赛程", "赛", "未来", "接下来", "即将", "下一场", "赛程安排"}
_STANDINGS_WORDS = {"standings", "排名", "积分", "榜", "排行"}


async def _api_football(path: str, params: dict) -> tuple[str | None, list]:
    """调用 api-football，返回 (错误信息或 None, response 数组)"""
    if not API_FOOTBALL_KEY:
        return "未配置 API-FOOTBALL-API-KEY（.env）", []
    import httpx

    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    try:
        async with httpx.AsyncClient(timeout=API_FOOTBALL_TIMEOUT) as client:
            r = await client.get(f"{API_FOOTBALL_BASE}{path}", params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("api-football 调用失败 %s: %s", path, exc)
        return f"api-football 调用失败: {exc}", []
    if data.get("errors"):
        return f"api-football 返回错误: {data['errors']}", []
    return None, data.get("response") or []


def _resolve_league(league: str) -> int | None:
    if not league:
        return None
    key = league.strip()
    return LEAGUE_IDS.get(key) or LEAGUE_IDS.get(key.lower())


async def _request_retry(path: str, base_params: dict, season: int, max_back: int = 5) -> tuple[int, str | None, list]:
    """带赛季回退的请求：免费套餐无权限访问该赛季 / 无数据时，回退更早赛季。返回 (有效赛季, 错误, 数据)"""
    last_err = None
    for s in range(season, season - max_back - 1, -1):
        params = {**base_params, "season": s}
        err, data = await _api_football(path, params)
        if err:
            last_err = err
            if "no access" in err.lower() or "plan" in err.lower():
                continue  # 无权限访问该赛季 → 回退
            return s, err, data
        if data:
            return s, None, data
    return max(season - max_back, 0), last_err or "没有查到该赛季数据", []


async def _resolve_team_id(team: str) -> str | None:
    """球队名 → api-football team id（数字直接用）"""
    if not team:
        return None
    if team.isdigit():
        return team
    err, data = await _api_football("/teams", {"search": team})
    if err or not data:
        return None
    t = data[0].get("team", {})
    await _cache_team(t)
    return str(t.get("id")) if t.get("id") else None


# ==================== 格式化 ====================

def _fmt_standings(data: list, season: int) -> str:
    lines = [f"【{season} 赛季联赛排名】"]
    for block in data:
        league_block = block.get("league", {})
        standings = (league_block.get("standings") or [[]])[0]
        for item in standings:
            team = item.get("team", {})
            all_stat = item.get("all", {}) or {}
            logo = team.get("logo", "")
            badge = f"![{team.get('name', '')}]({logo})" if logo else ""
            lines.append(
                f"{item.get('rank', '?')}. {badge} {team.get('name')} "
                f"积分{item.get('points', 0)} 胜{all_stat.get('win', 0)}平{all_stat.get('draw', 0)}负{all_stat.get('lose', 0)} "
                f"净胜球{item.get('goalsDiff', 0)}"
            )
    return "\n".join(lines[:12]) if len(lines) > 1 else "没有查到排名数据"


def _fmt_fixtures(data: list) -> str:
    lines = []
    for fx in data:
        f = fx.get("fixture", {})
        league = fx.get("league", {})
        teams = fx.get("teams", {})
        goals = fx.get("goals", {}) or {}
        home, away = teams.get("home", {}), teams.get("away", {})
        date_s = (f.get("date") or "")[:16].replace("T", " ")
        status = f.get("status", {}).get("short", "")
        hs, as_ = goals.get("home"), goals.get("away")
        score = f"{hs} - {as_}" if hs is not None else "vs"
        h_logo = f"![{home.get('name', '')}]({home.get('logo', '')})" if home.get("logo") else home.get("name", "")
        a_logo = f"![{away.get('name', '')}]({away.get('logo', '')})" if away.get("logo") else away.get("name", "")
        lines.append(
            f"{date_s} | {h_logo} {score} {a_logo} [{status}] ({league.get('name', '')})"
        )
    return "\n".join(lines[:15]) if lines else "没有查到相关比赛"


def _fmt_teams(data: list) -> str:
    lines = []
    for item in data:
        t = item.get("team", {})
        logo = t.get("logo", "")
        badge = f"![{t.get('name', '')}]({logo})" if logo else t.get("name", "")
        lines.append(f"- {badge} | 国家:{t.get('country')} | 联赛:{t.get('name')}")
    return "\n".join(lines) if lines else "没有查到该球队"


def _fmt_players(data: list) -> str:
    lines = []
    for item in data:
        p = item.get("player", {})
        stat = (item.get("statistics") or [{}])[0]
        team = stat.get("team", {}).get("name", "")
        photo = p.get("photo", "")
        photo_md = f"![{p.get('name', '')}]({photo})" if photo else ""
        lines.append(
            f"- {photo_md} {p.get('name')} | 位置:{p.get('position')} 年龄:{p.get('age')} 国籍:{p.get('nationality')} 球队:{team}"
        )
    return "\n".join(lines[:10]) if lines else "没有查到该球员"


# ==================== 尽力缓存到本地表 ====================

async def _cache_team(team: dict) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await football_crud.upsert_team(
                db, name=team.get("name", ""), api_id=team.get("id"),
                country=team.get("country"), logo_url=team.get("logo"),
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("球队缓存失败: %s", exc)


async def _cache_fixtures(data: list) -> None:
    try:
        async with AsyncSessionLocal() as db:
            for fx in data:
                teams = fx.get("teams", {})
                home, away = teams.get("home", {}), teams.get("away", {})
                home_rec = await football_crud.upsert_team(
                    db, home.get("name", ""), api_id=home.get("id"), logo_url=home.get("logo")
                )
                away_rec = await football_crud.upsert_team(
                    db, away.get("name", ""), api_id=away.get("id"), logo_url=away.get("logo")
                )
                f = fx.get("fixture", {})
                goals = fx.get("goals", {}) or {}
                await football_crud.upsert_match(
                    db,
                    api_id=f.get("id"),
                    home_team=home.get("name", ""),
                    away_team=away.get("name", ""),
                    home_team_id=home_rec.id,
                    away_team_id=away_rec.id,
                    league=fx.get("league", {}).get("name"),
                    season=str(fx.get("league", {}).get("season") or ""),
                    round_=fx.get("league", {}).get("round"),
                    match_date=f.get("date"),
                    status=f.get("status", {}).get("short"),
                    home_score=goals.get("home"),
                    away_score=goals.get("away"),
                    venue=f.get("venue", {}).get("name"),
                )
    except Exception as exc:  # noqa: BLE001
        logger.debug("比赛缓存失败: %s", exc)


# ==================== 主逻辑 ====================

async def _get_match_result(intent: str, league: str, season: int, team: str, date: str) -> str:
    intent = (intent or "result").strip().lower()
    season = season or API_FOOTBALL_SEASON
    league_id = _resolve_league(league)

    # 排名
    if intent in _STANDINGS_WORDS:
        if not league_id:
            return "查询联赛排名需要提供联赛名（如：英超）"
        used_season, err, data = await _request_retry("/standings", {"league": league_id}, season)
        if err:
            return err
        return _fmt_standings(data, used_season)

    # 球队资料
    if intent in ("team", "球队"):
        params = {"id": team} if team.isdigit() else ({"search": team} if team else {})
        if not params:
            return "查询球队需要提供球队名"
        err, data = await _api_football("/teams", params)
        if err:
            return err
        for item in data:
            await _cache_team(item.get("team", {}))
        return _fmt_teams(data)

    # 球员资料
    if intent in ("player", "球员"):
        if not team:
            return "查询球员需要提供球员名"
        params = {"search": team}
        if league_id:
            params["league"] = league_id
            params["season"] = season
        err, data = await _api_football("/players", params)
        if err:
            return err
        return _fmt_players(data)

    # 比赛结果 / 赛程 → /fixtures
    params: dict = {}
    if league_id:
        params["league"] = league_id
    team_id = team if team.isdigit() else await _resolve_team_id(team)
    if team_id:
        params["team"] = team_id

    today = datetime.now().date()
    if date:
        params["date"] = date
    elif intent in _SCHEDULE_WORDS:
        params["from"] = str(today)
        params["to"] = str(today + timedelta(days=7))
    else:  # result
        params["status"] = "FT"

    if league_id or team_id:
        # 有联赛/球队筛选时按赛季查，免费套餐无权限则自动回退
        used_season, err, data = await _request_retry("/fixtures", params, season)
    else:
        # 仅按日期查（不带赛季筛选，避免 date+season 冲突）
        err, data = await _api_football("/fixtures", params)
    if err:
        return err
    await _cache_fixtures(data)
    return _fmt_fixtures(data)


def build_football_tools() -> list[BaseTool]:
    @tool
    @log_tool_call
    async def get_match_result(
        intent: str,
        league: str = "",
        season: int = 0,
        team: str = "",
        date: str = "",
    ) -> str:
        """获取实时足球数据（api-football）。用户询问比赛结果/赛程/联赛排名/球队或球员资料时调用。

        intent 必填：result(比赛结果)/schedule(比赛赛程)/standings(联赛排名)/team(球队资料)/player(球员资料)。
        league：联赛名（英超/西甲/意甲/德甲/法甲/中超/欧冠/世界杯，或英文 Premier League 等），查排名必须填。
        season：赛季年份（默认当前赛季，可不填）；team：球队名或球员名；date：日期 YYYY-MM-DD。
        """
        return await _get_match_result(intent, league, season, team, date)

    return [get_match_result]
