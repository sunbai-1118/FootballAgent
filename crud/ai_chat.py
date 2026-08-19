"""AI 聊天相关数据库操作(含会话 ID 与 Agent 工具调用轨迹、回答反馈)"""
import json
from typing import List, Optional, Tuple

from opentelemetry.trace import format_trace_id, get_current_span
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_chat import AiChat
from models.answer_feedback import AnswerFeedback


def _current_trace_id() -> Optional[str]:
    """取当前 OTel span 的 trace_id（无则 None），用于 ai_chat 落库关联反馈/日志"""
    span = get_current_span()
    sc = span.get_span_context() if span is not None else None
    if sc is not None and sc.is_valid:
        return format_trace_id(sc.trace_id)
    return None


async def add_chat(
    db: AsyncSession,
    user_id: int,
    message: str,
    response: str,
    session_id: Optional[str] = None,
    agent_trace: Optional[list] = None,
) -> AiChat:
    """保存一条 AI 对话记录(用户消息 + AI 回复 + 会话ID + Agent 工具调用轨迹 + trace_id)"""
    record = AiChat(
        user_id=user_id,
        message=message,
        response=response,
        session_id=session_id,
        agent_trace=(
            json.dumps(agent_trace, ensure_ascii=False, default=str) if agent_trace else None
        ),
        trace_id=_current_trace_id(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def add_feedback(
    db: AsyncSession,
    ai_chat_id: Optional[int],
    user_id: int,
    score: str,
    reason: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> AnswerFeedback:
    """保存一条回答反馈(👍/👎)，用于优化 Prompt/RAG/Tool"""
    record = AnswerFeedback(
        ai_chat_id=ai_chat_id,
        user_id=user_id,
        trace_id=trace_id or _current_trace_id(),
        score=score,
        reason=reason,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_recent_history(
    db: AsyncSession,
    user_id: int,
    session_id: Optional[str] = None,
    limit: int = 5,
) -> List[Tuple[str, str]]:
    """获取最近的对话记录作为上下文，返回 [(用户消息, AI回复), ...] 时间正序

    - session_id 为 None:返回该用户全局最近 limit 组(兼容旧前端行为)
    - session_id 非 None:仅返回该会话内的最近 limit 组
    """
    stmt = select(AiChat).where(AiChat.user_id == user_id)
    if session_id:
        stmt = stmt.where(AiChat.session_id == session_id)
    result = await db.execute(stmt.order_by(AiChat.id.desc()).limit(limit))
    records = list(result.scalars().all())[::-1]  # 逆转为时间正序
    return [(r.message, r.response) for r in records]


async def get_session_history(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    limit: int = 50,
) -> List[AiChat]:
    """获取某会话的完整对话记录(时间正序)，供前端刷新页面后恢复对话"""
    result = await db.execute(
        select(AiChat)
        .where(AiChat.user_id == user_id, AiChat.session_id == session_id)
        .order_by(AiChat.id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
