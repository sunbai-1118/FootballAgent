"""用户个性化工具:收藏 / 浏览历史 / 长期记忆(remember)

复用 crud/favorite.py、crud/history.py 与 agents/memory_filter.py 记忆筛选层。
build_user_tools(user_id, session_id) 闭包捕获用户与会话，工具签名零参，LLM 无需传。
"""
from langchain_core.tools import BaseTool, tool

from agents.memory_filter import filter_fact
from agents.observability import log_tool_call
from config.db_conf import AsyncSessionLocal
from crud import favorite as fav_crud
from crud import history as his_crud


def _fmt_rows(rows, empty_msg: str) -> str:
    """格式化收藏/历史的联合查询行(SQLAlchemy Row,键与查询字段一一对应)"""
    if not rows:
        return empty_msg
    lines = []
    for r in rows:
        m = r._mapping
        line = f"- {m.get('title')}"
        if m.get("image"):
            line += f" (图片: {m['image']})"
        lines.append(line)
    return "\n".join(lines)


def build_user_tools(user_id: int, session_id: str) -> list[BaseTool]:
    @tool
    @log_tool_call
    async def get_my_favorites() -> str:
        """获取当前用户收藏的新闻列表(需登录用户,含图片URL)。用户问"我收藏了哪些/我的收藏"时调用。"""
        async with AsyncSessionLocal() as db:
            rows, _, _ = await fav_crud.get_favorite_list(db, user_id, page=1, page_size=10)
        return _fmt_rows(rows, "你还没有收藏任何新闻")

    @tool
    @log_tool_call
    async def get_my_history() -> str:
        """获取当前用户最近浏览的新闻列表(需登录用户,含图片URL)。用户问"我看过哪些/我的浏览历史"时调用。"""
        async with AsyncSessionLocal() as db:
            rows, _, _ = await his_crud.get_history_list(db, user_id, page=1, page_size=10)
        return _fmt_rows(rows, "你还没有浏览记录")

    @tool
    @log_tool_call
    async def remember(fact: str) -> str:
        """记住用户的一个长期偏好或事实（如喜欢的球队、关注的联赛、习惯称呼、个人身份）。用户明确表达个人偏好时调用。"""
        ok, result = await filter_fact(user_id, session_id, fact)
        return f"已记住：{result}" if ok else result

    return [get_my_favorites, get_my_history, remember]
