"""Verifier Node：回答可信度校验（Agent → Answer → Verifier → 检查事实来源 → 返回）

对最终回答做一次 LLM 二次校验：拿「问题 + 答案 + 证据（工具返回的真实数据）」判断是否 grounded，
输出结构化 {grounded, corrected_reply, note}；grounded=false 时用 corrected_reply 降幻觉。
"""
import json
import logging

from agents.model_factory import LLMFactory

logger = logging.getLogger(__name__)

_VERIFIER_PROMPT = """你是回答可信度校验器。判断 AI 的回答是否**有事实依据**，减少幻觉。

问题：{question}

AI 回答：
{answer}

用户记忆（用户本人的陈述，来自系统提示词，是**有效依据**）：
{user_memory}

工具证据（工具返回的真实数据 / 检索结果）：
{evidence}

校验规则：
1. **用户记忆相关回答**（如"我的主队是X/我收藏了…/我最近看过…"）：以用户记忆为准，视为有依据 → grounded=true。
2. **世界公开事实**（新闻/比赛/球员/排名/时效信息）：必须能在**工具证据**中找到支持；找不到 → grounded=false，
   给出 corrected_reply：删掉无依据内容、仅基于证据/记忆重写；确实不足时如实说明"该信息未在数据源中找到"。
3. 只输出 JSON：{{"grounded": true/false, "corrected_reply": "修正后回答(grounded=true 时可留空)", "note": "一句话说明"}}
"""


def _parse(text: str) -> dict:
    try:
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start : end + 1]) if 0 <= start < end else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Verifier 输出解析失败：%.200s", text)
        return {}


async def verify_answer(question: str, answer: str, evidence: str, user_memory: dict | None = None) -> dict:
    """返回 {"grounded": bool, "corrected_reply": str, "note": str}；异常时保守返回 grounded=True 不拦截

    :param user_memory: 记忆上下文 {long_term, summary, key_facts}，用户记忆是有效依据（避免误判"我的主队"等记忆回答）
    """
    memory_block = ""
    if user_memory:
        parts = []
        long_term = user_memory.get("long_term") or []
        if long_term:
            parts.append("长期记忆：" + "；".join(long_term))
        key_facts = user_memory.get("key_facts") or []
        if key_facts:
            parts.append("关键事实：" + json.dumps(key_facts, ensure_ascii=False))
        summary = user_memory.get("summary") or ""
        if summary:
            parts.append("会话摘要：" + summary)
        memory_block = "\n".join(parts)
    try:
        llm = LLMFactory.get_chat_model(temperature=0)
        prompt = _VERIFIER_PROMPT.format(
            question=question, answer=answer,
            user_memory=memory_block or "（无）", evidence=evidence or "（无）",
        )
        resp = await llm.ainvoke(prompt)
        text = ((getattr(resp, "content", "") or "")).strip()
        result = _parse(text)
        grounded = bool(result.get("grounded"))
        corrected = str(result.get("corrected_reply") or "").strip()
        note = str(result.get("note") or "").strip()
        if not grounded and not corrected and not note:
            # 校验输出残缺(截断/解析失败)：视为无结论，不拦截、不标记
            logger.warning("Verifier 输出残缺，跳过修正: grounded=false 但无校正/说明")
            grounded = True
        return {"grounded": grounded, "corrected_reply": corrected, "note": note}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Verifier 校验失败: %s", exc)
        return {"grounded": True, "corrected_reply": "", "note": ""}
