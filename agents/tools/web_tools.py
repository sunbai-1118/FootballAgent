"""联网工具:Tavily 文本搜索 + 自动配图(DB 优先 → SerpAPI 联网兜底)

文本搜索与图片搜索分离,分别走各自 API 额度:
- web_search           -> Tavily(文本)
- pick_illustration    -> ①本站 Qdrant retrieve_images(达阈值) ②SerpAPI google_images
"""
import logging

from langchain_core.tools import BaseTool, tool

from agents.observability import log_tool_call
from agents.rag import retrieve_images
from config.rag_conf import (
    IMAGE_SEARCH_TOP_K,
    IMAGE_SIM_THRESHOLD,
    SERPAPI_IMAGE_ENGINE,
    SERPAPI_KEY,
    TAVILY_API_KEY,
    WEB_SEARCH_TOP_K,
)

logger = logging.getLogger(__name__)


async def _tavily_search(query: str, k: int) -> str:
    """Tavily 文本搜索,返回格式化结果"""
    import httpx

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": k,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://api.tavily.com/search", json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily 搜索失败: %s", exc)
        return f"Tavily 搜索失败: {exc}"

    results = data.get("results") or []
    if not results:
        return "Tavily 没有搜索到相关结果"
    lines = []
    for item in results[:k]:
        title = item.get("title", "")
        url = item.get("url", "")
        content = (item.get("content") or "")[:200]
        lines.append(f"- {title}\n  {url}\n  {content}")
    return "\n\n".join(lines)


async def _serpapi_images(query: str, k: int) -> str:
    """SerpAPI Google Images 搜索,返回图片 URL 列表"""
    import httpx

    params = {
        "engine": SERPAPI_IMAGE_ENGINE,
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": k,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get("https://serpapi.com/search", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("SerpAPI 图片搜索失败: %s", exc)
        return f"SerpAPI 图片搜索失败: {exc}"

    imgs = data.get("images_results") or []
    if not imgs:
        return "SerpAPI 没有搜索到相关图片"
    lines = []
    for img in imgs[:k]:
        title = img.get("title", "")
        url = img.get("original") or img.get("thumbnail") or ""
        if url:
            lines.append(f"- {title} 图片URL: {url}")
    return "\n\n".join(lines) if lines else "SerpAPI 没有搜索到相关图片"


def build_web_tools() -> list[BaseTool]:
    @tool
    @log_tool_call
    async def web_search(query: str) -> str:
        """联网搜索(Tavily 文本):获取实时信息,如最新比分、转会传闻、球员伤病、赛程等本站数据库没有的时效性内容。返回标题+链接+摘要。"""
        if not TAVILY_API_KEY:
            return "未配置 TAVILY_API_KEY,无法联网搜索"
        return await _tavily_search(query, WEB_SEARCH_TOP_K)

    @tool
    @log_tool_call
    async def pick_illustration(query: str) -> str:
        """自动配图:为一条新闻/主题挑选图片。优先从本站数据库匹配(需达到相似度阈值),匹配不到再联网(SerpAPI Google Images)搜索。返回候选图片URL列表。"""
        # ① DB 优先
        payloads = await retrieve_images(query, k=IMAGE_SEARCH_TOP_K, min_score=IMAGE_SIM_THRESHOLD)
        db_lines = [
            f"- [本站] {p.get('title')} 图片URL: {p['image']}"
            for p in payloads
            if p.get("image")
        ]
        if db_lines:
            return "本站图片:\n" + "\n".join(db_lines)
        # ② 联网兜底
        if not SERPAPI_KEY:
            return "本站没有合适图片,且未配置 SERPAPI_KEY,无法联网取图"
        web_lines = await _serpapi_images(query, IMAGE_SEARCH_TOP_K)
        return "本站无合适图片,联网图片:\n" + web_lines

    return [web_search, pick_illustration]
