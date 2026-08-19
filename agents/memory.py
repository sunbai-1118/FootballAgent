"""Agent 记忆编排：token 预算 + 上下文加载 + 短期记忆压缩（summary/key_facts 分开生成）

短期记忆三层：
  summary        滚动摘要（自然语言，独立 LLM 生成）
  key_facts      结构化关键事实 JSON（独立 LLM 生成，同 key 覆盖）
  recent_messages 最近若干轮原文（存 ai_chat，用 summarized_upto 排除已折叠轮次）

压缩由 token 预算驱动：保留的 recent_messages 需同时满足轮数上限与 token 预算，
超出部分折叠进 summary + key_facts（两个独立 LLM 调用）。
"""
import json
import logging

from config.db_conf import AsyncSessionLocal
from crud import memory as memory_crud

logger = logging.getLogger(__name__)


# ==================== Token 预算（中文粗估：约 3 字符/token） ====================
def estimate_tokens(text: str) -> int:
    return len(text) // 3 if text else 0


CONTEXT_BUDGET_TOKENS = 16000     # 总上下文预算（给生成留余量）
SYSTEM_PROMPT_BUDGET = 1000       # 人设 + 时效 + 行为准则
MEMORY_BUDGET = 3000              # 长期记忆 + summary + key_facts 合计
RECENT_MESSAGES_BUDGET = 5000     # 最近原文（约 5~10 轮）
TOOLS_BUDGET = 4000               # 工具 schema（bind_tools 生成，预留、不可直接压缩）
QUERY_BUDGET = 2000               # 当前 query + 回复余量

RECENT_MAX_TURNS = 10             # recent_messages 轮数硬上限
USER_MEMORY_MAX_ITEMS = 20        # 注入长期记忆最大条数
SESSION_SUMMARY_MAX_CHARS = 2400  # summary 截断（约 800 token）
KEY_FACTS_MAX_ITEMS = 50          # key_facts 条数上限


def _fmt_turns(turns) -> str:
    """把 [(用户消息, AI回复), ...] 转成文本，供摘要/关键事实生成"""
    lines = []
    for i, (user_msg, ai_reply) in enumerate(turns, 1):
        lines.append(f"[轮次{i}]\n用户: {user_msg}\nAI: {ai_reply}")
    return "\n\n".join(lines)


async def load_memory_context(db, user_id: int, session_id: str) -> dict:
    """一次性加载记忆上下文，供 _prepare 拼 history 与 agent_node 拼 system prompt（闭包注入，不经 AgentState）

    返回：{"long_term": [str], "summary": str, "key_facts": [dict], "recent_messages": [(user,ai),...]}
    """
    memories = await memory_crud.get_user_memories(db, user_id, limit=USER_MEMORY_MAX_ITEMS)
    long_term = [m.content for m in memories]

    session_mem = await memory_crud.get_session_memory(db, user_id, session_id)
    summary = (session_mem.summary if session_mem else None) or ""
    summarized_upto = session_mem.summarized_upto if session_mem else 0
    key_facts: list = []
    if session_mem and session_mem.key_facts:
        try:
            key_facts = json.loads(session_mem.key_facts)
        except (json.JSONDecodeError, TypeError):
            key_facts = []

    # recent_messages：已折叠轮次之后、且在窗口内的最近轮次
    total = await memory_crud.count_session_turns(db, user_id, session_id)
    skip = max(summarized_upto, total - RECENT_MAX_TURNS)
    n = min(RECENT_MAX_TURNS, max(0, total - skip))
    recent_turns = await memory_crud.get_turns_range(db, user_id, session_id, skip, n)

    return {
        "long_term": long_term,
        "summary": summary,
        "key_facts": key_facts,
        "recent_messages": recent_turns,
    }


async def update_summary(old_summary: str, folded_turns, llm) -> str:
    """把溢出轮次折叠进 summary（自然语言叙述，独立 LLM 调用）"""
    prompt = (
        "你是会话记忆整理器。请把「旧摘要」与「新轮次」合并成一份更完整的滚动摘要，"
        "用简洁的自然语言叙述这段对话的脉络（用户问了什么、关注什么、发生了什么）。\n\n"
        f"旧摘要：\n{old_summary or '（无）'}\n\n"
        f"新轮次：\n{_fmt_turns(folded_turns)}\n\n"
        "只输出合并后的摘要正文，不要其他说明。"
    )
    resp = await llm.ainvoke(prompt)
    text = ((getattr(resp, "content", "") or "")).strip()
    return text[:SESSION_SUMMARY_MAX_CHARS]


async def update_key_facts(old_key_facts: list, folded_turns, llm) -> list:
    """把溢出轮次折叠进 key_facts（结构化 JSON，独立 LLM 调用，同 key 覆盖）"""
    prompt = (
        "你是会话事实提取器。从对话中提取值得跨轮次记住的「结构化关键事实」"
        "（如用户的偏好、身份、稳定信息；不要新闻知识、不要一次性查询）。\n\n"
        f"已有关键事实(JSON)：\n{json.dumps(old_key_facts, ensure_ascii=False) if old_key_facts else '[]'}\n\n"
        f"新轮次：\n{_fmt_turns(folded_turns)}\n\n"
        '请返回 JSON 数组，每项形如 {"key":"喜欢的球队","value":"曼联","updated_at":"2026-08-17"}。'
        "同 key 取最新值覆盖；无新事实返回 []。只输出 JSON。"
    )
    resp = await llm.ainvoke(prompt)
    text = ((getattr(resp, "content", "") or "")).strip()
    try:
        start, end = text.find("["), text.rfind("]")
        parsed = json.loads(text[start : end + 1]) if 0 <= start < end else []
    except (json.JSONDecodeError, TypeError):
        logger.warning("key_facts 解析失败，丢弃本轮折叠：%.200s", text)
        parsed = []
    merged = {f["key"]: f for f in old_key_facts if isinstance(f, dict) and f.get("key")}
    for item in parsed:
        if isinstance(item, dict) and item.get("key"):
            merged[item["key"]] = item
    return list(merged.values())[:KEY_FACTS_MAX_ITEMS]


async def maybe_compress(user_id: int, session_id: str, llm) -> None:
    """add_chat 后 fire-and-forget：未折叠轮次超出窗口/预算时，把最早轮次折叠进 summary + key_facts

    保留的 recent_messages 需同时满足：轮数 ≤ RECENT_MAX_TURNS 且 token ≤ RECENT_MESSAGES_BUDGET。
    自开 DB 会话，供后台任务调用。
    """
    try:
        async with AsyncSessionLocal() as db:
            session_mem = await memory_crud.get_session_memory(db, user_id, session_id)
            summarized_upto = session_mem.summarized_upto if session_mem else 0
            total = await memory_crud.count_session_turns(db, user_id, session_id)
            unsummarized = total - summarized_upto
            if unsummarized <= 1:
                return

            # 估算保留窗口的 token：取最近 RECENT_MAX_TURNS 轮
            start = max(summarized_upto, total - RECENT_MAX_TURNS)
            recent_window = await memory_crud.get_turns_range(db, user_id, session_id, start, RECENT_MAX_TURNS)
            acc = sum(estimate_tokens(u) + estimate_tokens(a) for u, a in recent_window)

            overflow = unsummarized - len(recent_window)
            if acc > RECENT_MESSAGES_BUDGET and recent_window:
                # 最近窗口超 token 预算：按平均 token 折算需再多折叠几轮
                avg = acc / len(recent_window)
                overflow = max(overflow, int((acc - RECENT_MESSAGES_BUDGET) / avg) + 1)
            overflow = min(overflow, unsummarized - 1)  # 至少保留 1 轮
            if overflow <= 0:
                return

            folded_turns = await memory_crud.get_turns_range(db, user_id, session_id, summarized_upto, overflow)
            if not folded_turns:
                return

            old_summary = (session_mem.summary if session_mem else None) or ""
            old_key_facts: list = []
            if session_mem and session_mem.key_facts:
                try:
                    old_key_facts = json.loads(session_mem.key_facts)
                except (json.JSONDecodeError, TypeError):
                    old_key_facts = []

            # summary 与 key_facts 由两个独立 LLM 过程生成（自然语言 vs 结构化）
            new_summary = await update_summary(old_summary, folded_turns, llm)
            new_key_facts = await update_key_facts(old_key_facts, folded_turns, llm)

            await memory_crud.upsert_session_memory(
                db,
                user_id,
                session_id,
                summary=new_summary,
                key_facts=json.dumps(new_key_facts, ensure_ascii=False),
                summarized_upto=summarized_upto + overflow,
            )
            logger.info("[memory] 压缩:折叠 %d 轮进 summary/key_facts", overflow)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[memory] 短期记忆压缩失败: %s", exc)
