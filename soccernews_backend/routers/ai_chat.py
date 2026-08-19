"""AI Agent 相关 API 路由"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents import agent_service
from agents import rag as agent_rag
from config.db_conf import get_db
from crud import ai_chat as ai_crud
from models.users import User
from schemas.ai_chat import AiChatRequest, AnswerFeedbackRequest
from utils.auth import get_current_user
from utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Agent 模块"])


@router.get("/history", summary="获取指定会话的对话历史（刷新页面后恢复对话）")
async def get_history(
    sessionId: str = Query(..., alias="sessionId", description="会话ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    records = await ai_crud.get_session_history(db, current_user.id, sessionId)
    messages = []
    for r in records:
        messages.append({"role": "user", "content": r.message})
        messages.append({"role": "assistant", "content": r.response})
    return success(data={"sessionId": sessionId, "messages": messages}, message="success")


@router.post("/rag/reindex", summary="重建 RAG 索引（全量：先删后建）")
async def reindex_rag(
    current_user: User = Depends(get_current_user),
):
    try:
        count = await agent_rag.index_news()
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG 重建索引失败：%s", exc)
        raise HTTPException(status_code=502, detail="RAG 重建索引失败，请检查 Qdrant / 嵌入服务是否就绪")
    return success(data={"indexed": count}, message="success")


@router.post("/chat", summary="AI Agent 对话（自动携带最近对话上下文，消息与工具轨迹落库）")
async def chat(
    data: AiChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await agent_service.chat(current_user.id, data.message, data.sessionId, db)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent 服务调用失败：%s", exc)
        raise HTTPException(status_code=502, detail="AI 服务调用失败，请检查 API Key、Docker 服务或网络")
    return success(data=result, message="success")


@router.post("/feedback", summary="提交回答反馈（👍/👎），用于优化 Prompt/RAG/Tool")
async def submit_feedback(
    data: AnswerFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await ai_crud.add_feedback(
            db, data.chatId, current_user.id, data.score, data.reason, data.traceId
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("保存反馈失败：%s", exc)
        raise HTTPException(status_code=500, detail="保存反馈失败")
    return success(data={"score": data.score}, message="反馈已记录")


@router.post("/chat/stream", summary="AI Agent 对话（SSE 流式 + 工具调用过程）")
async def chat_stream(
    data: AiChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式返回:工具调用状态 + 回答 token 逐块推送

    事件:session / tool_call / token / tool_done / done / error
    """

    async def event_gen():
        try:
            async for frame in agent_service.chat_stream(current_user.id, data.message, data.sessionId, db):
                yield frame
        except Exception as exc:  # noqa: BLE001
            logger.exception("SSE 流式对话异常: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': f'AI 服务调用失败: {exc}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
