"""图片相关工具：thesportsDB 球队/球员真实图片（get_match_pick）+ RAG 本站图片检索（retrieve_images_tool）

get_match_pick 代替 pick_illustration：用户要球队/球员图片时取真实图，不再随机联网。
"""
import logging
from typing import Any

from langchain_core.tools import BaseTool, tool

from agents.observability import log_tool_call
from agents.rag import retrieve_images
from config.football_conf import THESPORTDB_BASE, THESPORTDB_KEY, THESPORTDB_TIMEOUT
from config.rag_conf import IMAGE_SIM_THRESHOLD

logger = logging.getLogger(__name__)


def _fmt_payloads(payloads: list[dict[str, Any]]) -> str:
    """格式化 RAG 检索到的图片 payload（含数据库图片URL）"""
    if not payloads:
        return "没有检索到相关结果"
    lines = []
    for p in payloads:
        line = f"[新闻 {p.get('news_id')}] {p.get('title')} 分类:{p.get('category') or '未知'}"
        if p.get("image"):
            line += f" 图片URL: {p['image']}"
        lines.append(line)
    return "\n\n".join(lines)


async def _thesportsdb(path: str, params: dict) -> tuple[str | None, list]:
    """调用 thesportsDB，返回 (错误信息或 None, response 数组)"""
    if not THESPORTDB_KEY:
        return "未配置 THESPORTDB-API-KEY（.env）", []
    import httpx

    url = f"{THESPORTDB_BASE}/{THESPORTDB_KEY}/{path}"
    try:
        async with httpx.AsyncClient(timeout=THESPORTDB_TIMEOUT) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("thesportsDB 调用失败 %s: %s", path, exc)
        return f"thesportsDB 调用失败: {exc}", []
    return None, data.get("teams") or data.get("player") or []


def build_image_tools() -> list[BaseTool]:
    @tool
    @log_tool_call
    async def get_match_pick(query: str) -> str:
        """为球队/球员挑选真实图片（thesportsDB）：先按队名搜队徽，再按球员名搜球员照，返回图片URL。用户要球队/球员图片时调用。"""
        err, teams = await _thesportsdb("searchteams.php", {"t": query})
        if err:
            return err
        if teams:
            lines = []
            for t in teams[:5]:
                badge = t.get("strBadge") or t.get("strLogo") or t.get("strBanner") or ""
                if badge:
                    lines.append(f"- {t.get('strTeam', '')} 队徽: {badge}")
            if lines:
                return "thesportsDB 队徽:\n" + "\n".join(lines)
        err, players = await _thesportsdb("searchplayers.php", {"p": query})
        if err:
            return err
        if players:
            lines = []
            for p in players[:5]:
                photo = p.get("strCutout") or p.get("strThumb") or p.get("strRender") or ""
                if photo:
                    lines.append(f"- {p.get('strPlayer', '')} 球员照: {photo}")
            if lines:
                return "thesportsDB 球员照:\n" + "\n".join(lines)
        return "thesportsDB 没有找到相关图片"

    @tool
    @log_tool_call
    async def retrieve_images_tool(query: str) -> str:
        """多模态图片检索（RAG text→image）：按文字描述找本站达相似度阈值(IMAGE_SIM_THRESHOLD)的图片URL。用户要本站新闻相关图片时调用。"""
        payloads = await retrieve_images(query, k=5, min_score=IMAGE_SIM_THRESHOLD)
        return _fmt_payloads(payloads)

    return [get_match_pick, retrieve_images_tool]
