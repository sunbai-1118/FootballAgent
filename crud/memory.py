"""记忆相关数据库操作：用户长期记忆(user_memory) + 会话短期记忆(session_memory)

长期记忆经 agents/memory_filter.py 筛选层入库；短期记忆三层中 summary/key_facts 存 session_memory，
recent_messages 直接查 ai_chat（用 summarized_upto 排除已折叠轮次）。
"""
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_chat import AiChat
from models.session_memory import SessionMemory
from models.user_memory import UserMemory


# ==================== 长期记忆（user_memory） ====================

async def get_user_memories(
    db: AsyncSession, user_id: int, limit: int = 20
) -> List[UserMemory]:
    """获取用户长期记忆，按重要性降序、新近优先"""
    stmt = (
        select(UserMemory)
        .where(UserMemory.user_id == user_id)
        .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_user_memory(
    db: AsyncSession,
    user_id: int,
    content: str,
    memory_type: str = "preference",
    importance: int = 3,
    source_session_id: Optional[str] = None,
) -> UserMemory:
    """写入一条长期记忆（同 user+content 去重，更新 importance/来源）"""
    existing = await db.execute(
        select(UserMemory).where(
            UserMemory.user_id == user_id, UserMemory.content == content
        )
    )
    record = existing.scalar_one_or_none()
    if record is not None:
        record.memory_type = memory_type
        record.importance = importance
        record.source_session_id = source_session_id
        await db.commit()
        await db.refresh(record)
        return record
    record = UserMemory(
        user_id=user_id,
        content=content,
        memory_type=memory_type,
        importance=importance,
        source_session_id=source_session_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


# ==================== 会话短期记忆（session_memory） ====================

async def get_session_memory(
    db: AsyncSession, user_id: int, session_id: str
) -> Optional[SessionMemory]:
    result = await db.execute(
        select(SessionMemory).where(
            SessionMemory.user_id == user_id, SessionMemory.session_id == session_id
        )
    )
    return result.scalar_one_or_none()


async def upsert_session_memory(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    summary: Optional[str] = None,
    key_facts: Optional[str] = None,
    summarized_upto: Optional[int] = None,
) -> SessionMemory:
    """写入/更新会话短期记忆（每 session 一行）"""
    record = await get_session_memory(db, user_id, session_id)
    if record is None:
        record = SessionMemory(user_id=user_id, session_id=session_id)
        db.add(record)
    if summary is not None:
        record.summary = summary
    if key_facts is not None:
        record.key_facts = key_facts
    if summarized_upto is not None:
        record.summarized_upto = summarized_upto
    await db.commit()
    await db.refresh(record)
    return record


# ==================== 会话轮次（ai_chat，供 recent_messages 与压缩折叠） ====================

async def count_session_turns(db: AsyncSession, user_id: int, session_id: str) -> int:
    """统计某会话的对话轮数（一轮 = 一条 ai_chat 记录）"""
    result = await db.execute(
        select(func.count(AiChat.id)).where(
            AiChat.user_id == user_id, AiChat.session_id == session_id
        )
    )
    return int(result.scalar_one() or 0)


async def get_turns_range(
    db: AsyncSession, user_id: int, session_id: str, skip: int, limit: int
) -> List[Tuple[str, str]]:
    """按轮次下标取对话 [(用户消息, AI回复)]，时间正序（skip 从最老轮次计）"""
    stmt = (
        select(AiChat)
        .where(AiChat.user_id == user_id, AiChat.session_id == session_id)
        .order_by(AiChat.id.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(r.message, r.response) for r in result.scalars().all()]
