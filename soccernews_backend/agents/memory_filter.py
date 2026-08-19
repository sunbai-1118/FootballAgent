"""长期记忆筛选判断层：决定什么值得记、什么不该记

RAG/Memory 边界：只有「关于用户个人的持久信息」进 Memory；公开事实/新闻知识走 RAG 检索。

流程：
  1. 规则预过滤（含个人偏好关键词才继续，快速拦截闲聊）；
  2. LLM 判断（持久性 / 个性化 / 重要性 / 去重冲突，输出 keep/action/reason）；
  3. 只有 keep=true 且 action=add/update 的入库。

所有写操作自开 AsyncSessionLocal 会话（供 remember 工具与 fire-and-forget 合并复用）。
"""
import json
import logging

from agents.model_factory import LLMFactory
from config.db_conf import AsyncSessionLocal
from crud import memory as memory_crud

logger = logging.getLogger(__name__)


def _get_judge_llm():
    """记忆判断用 LLM：temperature=0 输出更确定（结构化 JSON）"""
    return LLMFactory.get_chat_model(temperature=0)

# 规则预过滤关键词：命中才值得走 LLM 判断（快速拦截无关内容）
_PREFERENCE_KEYWORDS = ("喜欢", "关注", "我的", "我是", "支持", "偏好", "习惯", "记住", "球迷", "不看")

_FILTER_PROMPT = """你是用户记忆管理员。根据下面这段对话，判断有哪些**值得长期记住**的用户记忆候选。

判断标准（四条，任一不满足则 reject）：
1. 持久性：随时间稳定成立的事实/偏好；一次性查询、临时消息、今天比分等拒绝。
2. 个性化：关于"这个用户"的偏好/身份/习惯/称呼；公开的新闻/球员/赛事知识拒绝（那是 RAG 该管的）。
3. 重要性：会影响后续对话的稳定信号；寒暄、无关闲聊拒绝。
4. 去重/冲突：与已有记忆对比，给出 add(新增)/update(替换同主题旧记忆)/ignore(重复或无价值)。

现有用户记忆：
{existing}

本轮对话：
用户：{user_msg}
AI：{ai_reply}

只输出 JSON，形如：
{{"candidates":[{{"content":"用户喜欢的球队是曼联","type":"preference","keep":true,"action":"add","importance":4,"reason":"持久个性化偏好"}},{{"content":"...","type":"...","keep":false,"action":"ignore","reason":"..."}}]}}
"""


def _parse_candidates(text: str) -> list:
    try:
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1]) if 0 <= start < end else {}
        return data.get("candidates") or []
    except (json.JSONDecodeError, TypeError):
        logger.warning("记忆筛选输出解析失败：%.200s", text)
        return []


async def judge_turn(db, user_id: int, user_msg: str, ai_reply: str, llm) -> list[dict]:
    """对一轮对话做 LLM 记忆判断，返回需入库的候选 [{content,type,action,importance}]"""
    existing_rows = await memory_crud.get_user_memories(db, user_id, limit=50)
    existing_text = "\n".join(f"- {m.content}" for m in existing_rows) or "（无）"
    prompt = _FILTER_PROMPT.format(existing=existing_text, user_msg=user_msg, ai_reply=ai_reply)
    resp = await llm.ainvoke(prompt)
    text = ((getattr(resp, "content", "") or "")).strip()
    candidates = _parse_candidates(text)
    kept = []
    for c in candidates:
        if isinstance(c, dict) and c.get("keep") and c.get("action") in ("add", "update"):
            content = str(c.get("content", "")).strip()
            if content:
                kept.append({
                    "content": content,
                    "type": c.get("type") or "preference",
                    "importance": max(1, min(5, int(c.get("importance") or 3))),
                })
    return kept


async def consolidate_turn(user_id: int, session_id: str, user_msg: str, ai_reply: str) -> None:
    """对话结束后 fire-and-forget：筛选并写入长期记忆（自开 DB 会话 + 自建判断 LLM）"""
    try:
        llm = _get_judge_llm()
        async with AsyncSessionLocal() as db:
            kept = await judge_turn(db, user_id, user_msg, ai_reply, llm)
            for k in kept:
                await memory_crud.upsert_user_memory(
                    db, user_id, k["content"],
                    memory_type=k["type"], importance=k["importance"],
                    source_session_id=session_id,
                )
            if kept:
                logger.info("[memory] 长期记忆合并:新增/更新 %d 条", len(kept))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[memory] 长期记忆合并失败: %s", exc)


async def filter_fact(user_id: int, session_id: str, fact: str) -> tuple[bool, str]:
    """remember 工具的判断入口：规则预过滤 + LLM 判断，返回 (是否入库, 提示语)"""
    if not any(kw in fact for kw in _PREFERENCE_KEYWORDS):
        return False, "这条不像持久个人偏好，未记录"
    try:
        llm = _get_judge_llm()
        async with AsyncSessionLocal() as db:
            kept = await judge_turn(db, user_id, fact, "", llm)
            if kept:
                k = kept[0]
                await memory_crud.upsert_user_memory(
                    db, user_id, k["content"],
                    memory_type=k["type"], importance=k["importance"],
                    source_session_id=session_id,
                )
                return True, k["content"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[memory] remember 判断失败: %s", exc)
    return False, "经判断这条信息不需要长期记住"
