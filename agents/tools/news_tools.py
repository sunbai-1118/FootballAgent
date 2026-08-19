"""新闻相关工具:关键词搜索 / 详情 / 热门 / 文本 RAG 检索

复用 crud/news.py 的数据库查询与 agents/rag.py 的文本检索。
每个工具自行通过 AsyncSessionLocal 开启独立会话,避免并发复用同一会话。
（图片工具 retrieve_images_tool 已迁至 agents/tools/image_tools.py）
"""
from typing import Any

from langchain_core.tools import BaseTool, tool

from agents.observability import log_tool_call
from agents.rag import retrieve_news
from config.db_conf import AsyncSessionLocal
from crud import news as news_crud


def _fmt_news(news) -> str:
    if news is None:
        return "未找到该新闻"
    content = news.content or ""
    return (
        f"[新闻 {news.id}] {news.title}\n"
        f"{news.description or ''}\n"
        f"内容: {content[:300]}{'...' if len(content) > 300 else ''}\n"
        f"图片: {news.image or '无'}"
    )


def _fmt_news_list(rows) -> str:
    if not rows:
        return "没有找到相关新闻"
    lines = []
    for n in rows:
        brief = n.description or (n.content or "")[:60] or ""
        lines.append(
            f"[新闻 {n.id}] {n.title}\n"
            f"  摘要: {brief}\n"
            f"  图片: {n.image or '无'}"
        )
    return "\n\n".join(lines)


def _fmt_payloads(payloads: list[dict[str, Any]]) -> str:
    """格式化 RAG 检索到的 point payload(含数据库中的图片URL)"""
    if not payloads:
        return "没有检索到相关结果"
    lines = []
    for p in payloads:
        line = f"[新闻 {p.get('news_id')}] {p.get('title')} 分类:{p.get('category') or '未知'}"
        if p.get("image"):
            line += f" 图片URL: {p['image']}"
        lines.append(line)
    return "\n\n".join(lines)


def build_news_tools() -> list[BaseTool]:
    @tool
    @log_tool_call
    async def search_news(keyword: str) -> str:
        """按关键词搜索新闻标题/内容,返回 Top-N 新闻列表(标题+摘要+ID+分类+图片URL)。用户想找某主题的新闻时调用。"""
        async with AsyncSessionLocal() as db:
            rows = await news_crud.search_news(db, keyword, limit=5)
        return _fmt_news_list(rows)

    @tool
    @log_tool_call
    async def get_news_detail(news_id: int) -> str:
        """按 ID 获取新闻完整内容(含图片URL)。已在对话中提到具体新闻ID或想了解某条新闻全文时调用。"""
        async with AsyncSessionLocal() as db:
            news = await news_crud.get_news_detail(db, news_id)
        return _fmt_news(news)

    @tool
    @log_tool_call
    async def retrieve_news_tool(query: str) -> str:
        """语义检索(多模态RAG text→text):根据问题检索本站相关新闻,返回标题+分类+图片URL。回答新闻/赛事/球员等事实问题前应优先调用。"""
        payloads = await retrieve_news(query, k=5)
        return _fmt_payloads(payloads)

    @tool
    @log_tool_call
    async def get_hot_news() -> str:
        """获取热门新闻(按浏览量排序,含标题+图片URL)。用户问"最新/热门/大家都在看"的新闻时调用。"""
        async with AsyncSessionLocal() as db:
            rows = await news_crud.get_hot_news(db, limit=5)
        return _fmt_news_list(rows)

    return [search_news, get_news_detail, retrieve_news_tool, get_hot_news]
