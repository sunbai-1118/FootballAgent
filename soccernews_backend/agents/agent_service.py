"""Agent 对外服务:组装历史 + 构建图 + 执行(一次性 / SSE 流式)+ 落库 + 记忆维护"""
import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from agents import memory as memory_module
from agents import verifier as verifier_module
from agents.graph import build_agent_graph
from agents.memory_filter import consolidate_turn
from agents.observability import _short, logger as agent_logger
from agents.model_factory import LLMFactory
from agents.tools.football_tools import build_football_tools
from agents.tools.image_tools import build_image_tools
from agents.tools.news_tools import build_news_tools
from agents.tools.registry import ToolRegistry
from agents.tools.user_tools import build_user_tools
from agents.tools.web_tools import build_web_tools
from config.ai_conf import VERIFIER_ENABLED
from config.otel_conf import tracer
from crud import ai_chat as ai_crud
from utils.log_context import bind

logger = logging.getLogger(__name__)


# ==================== 内部工具 ====================

def _extract_last_text(messages) -> str:
    """取最后一个非空的 AI 消息文本作为最终回复"""
    for m in reversed(messages):
        if getattr(m, "type", "") == "ai" and getattr(m, "content", ""):
            return m.content
    return ""


def _sse(data: dict) -> str:
    """SSE 数据帧: data: {json}\n\n"""
    return f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _chunk_text(chunk) -> str:
    """提取 AIMessageChunk 的纯文本(content 可能为 str 或内容块列表)"""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return ""


def _content_str(output) -> str:
    """提取模型输出的完整文本"""
    content = getattr(output, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content) if content else ""


def _tool_name(tc) -> str:
    """从 tool_call(dict 或对象)取工具名"""
    if isinstance(tc, dict):
        return tc.get("name") or ""
    return getattr(tc, "name", "") or ""


def _extract_evidence(messages, limit: int = 4000) -> str:
    """从图结果消息里提取工具返回的真实数据作为 Verifier 证据"""
    parts = []
    for m in messages:
        if getattr(m, "type", "") == "tool":
            content = getattr(m, "content", "")
            if content:
                parts.append(str(content))
    return "\n".join(parts)[:limit]


async def _prepare(user_id: int, message: str, session_id: str | None, db):
    """公共准备:加载记忆上下文、建图、组输入;返回 (session_id, graph, inputs, llm)"""
    if not session_id:
        # 不传 sessionId(旧前端兜底):生成新会话，recent 从空开始，但长期记忆照常注入
        session_id = str(uuid4())

    llm = LLMFactory.get_chat_model()
    # 记忆上下文(长期记忆 + 会话 summary/key_facts + recent_messages)一次性加载，
    # 以闭包传入 graph 供 agent_node 拼 system prompt，不放进 AgentState
    memory_ctx = await memory_module.load_memory_context(db, user_id, session_id)
    registry = ToolRegistry().register_many(
        *build_news_tools(),                       # 新闻：搜索/详情/热门/文本RAG
        *build_user_tools(user_id, session_id),    # 用户：收藏/历史/remember
        *build_image_tools(),                      # 图片：get_match_pick(thesportsDB)/retrieve_images_tool
        *build_football_tools(),                   # 足球实时：get_match_result(api-football)
        *build_web_tools(),                        # 联网：web_search(新闻兜底)
    )
    graph = build_agent_graph(llm, registry.all(), memory_context=memory_ctx)

    history_msgs: list = []
    for user_msg, ai_reply in memory_ctx["recent_messages"]:
        history_msgs.append(HumanMessage(content=user_msg))
        history_msgs.append(AIMessage(content=ai_reply))

    inputs = {
        "messages": history_msgs + [HumanMessage(content=message)],
        "user_id": user_id,
        "session_id": session_id,
        "agent_trace": [],
    }
    # 把业务上下文写入当前任务：后续 graph/llm/rag/tool 日志与 span 都带 user_id/session_id
    bind(user_id=user_id, session_id=session_id)
    return session_id, graph, inputs, llm, memory_ctx


# ==================== 一次性对话 ====================

async def chat(user_id: int, message: str, session_id: str | None, db) -> dict:
    """Agent 对话入口(一次性返回完整回复)

    :return: {"sessionId", "reply", "agentTrace", "createTime"}
    """
    start = time.perf_counter()
    session_id, graph, inputs, llm, memory_ctx = await _prepare(user_id, message, session_id, db)
    agent_logger.info(
        "[chat] 开始 user=%s session=%s msg=%s",
        user_id, session_id[:8], _short(message, 120),
        extra={"chat": {"event": "start", "user_id": user_id, "session_id": session_id[:8],
                        "msg": _short(message, 120)}},
    )
    trace: list = []
    final_reply = ""
    result = None
    try:
        with tracer.start_as_current_span("agent.chat") as span:
            span.set_attributes({"user_id": user_id, "session_id": session_id})
            result = await graph.ainvoke(
                inputs,
                config={"recursion_limit": 15},  # 兜底防死循环
            )
        final_reply = _extract_last_text(result["messages"])
        trace = result.get("agent_trace", [])
    except GraphRecursionError:
        # 工具循环触底：友好降级，不崩
        logger.warning("Agent 检索次数过多(user=%s),已降级回答", user_id)
        final_reply = "抱歉，检索次数过多未能找到确切答案。请换个问法，或明确一下你想了解的球队/比赛/球员。"

    # Verifier 校验（可配置）：拿问题+答案+工具证据，grounded=false 时用校正后回复
    verified = None
    if VERIFIER_ENABLED and final_reply:
        evidence = _extract_evidence(result["messages"]) if result else ""
        verified = await verifier_module.verify_answer(message, final_reply, evidence, user_memory=memory_ctx)
        if not verified["grounded"] and verified["corrected_reply"]:
            final_reply = verified["corrected_reply"]

    record = await ai_crud.add_chat(
        db, user_id, message, final_reply,
        session_id=session_id,
        agent_trace=trace,
    )
    # 记忆维护（fire-and-forget，不阻塞响应）：
    # ① 短期记忆压缩(超预算折叠进 summary/key_facts) ② 长期记忆合并(筛选判断入库)
    asyncio.create_task(memory_module.maybe_compress(user_id, session_id, llm))
    asyncio.create_task(consolidate_turn(user_id, session_id, message, final_reply))
    elapsed_s = round(time.perf_counter() - start, 1)
    agent_logger.info(
        "[chat] 完成 user=%s session=%s reply=%d字符 耗时%.1fs trace=%s",
        user_id, session_id[:8], len(final_reply), elapsed_s, trace,
        extra={"chat": {"event": "end", "user_id": user_id, "session_id": session_id[:8],
                        "reply_len": len(final_reply), "elapsed_s": elapsed_s, "trace": trace}},
    )
    return {
        "chatId": record.id,
        "sessionId": session_id,
        "reply": final_reply,
        "agentTrace": trace,
        "createTime": record.created_at,
    }


# ==================== SSE 流式对话 ====================

async def chat_stream(
    user_id: int, message: str, session_id: str | None, db
) -> AsyncGenerator[str, None]:
    """Agent 对话入口(SSE 流式,按事件推送工具状态与回答 token)

    事件帧(data: json):
      {"type":"session",   "sessionId": ...}                        会话建立
      {"type":"tool_call", "tool": ["name", ...]}                   模型决定调用工具
      {"type":"token",     "content": "..."}                        回答文本增量
      {"type":"tool_done", "tool": "name"}                          工具执行完成
      {"type":"done",      "sessionId", "agentTrace", "reply", "createTime"}  完成
      {"type":"error",     "message": ...}                          出错
    """
    session_id, graph, inputs, llm, memory_ctx = await _prepare(user_id, message, session_id, db)
    agent_logger.info(
        "[stream] 开始 user=%s session=%s msg=%s",
        user_id, session_id[:8], _short(message, 120),
        extra={"chat": {"event": "start", "stream": True, "user_id": user_id,
                        "session_id": session_id[:8], "msg": _short(message, 120)}},
    )
    yield _sse({"type": "session", "sessionId": session_id})

    trace: list = []
    final_reply = ""
    cur_buf: list[str] = []  # 当前模型调用的 token 缓冲
    tool_outputs: list = []  # 工具返回数据（Verifier 证据）

    try:
        with tracer.start_as_current_span("agent.chat_stream") as span:
            span.set_attributes({"user_id": user_id, "session_id": session_id})
            async for event in graph.astream_events(inputs, config={"recursion_limit": 15}, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_start":
                    cur_buf = []
                elif kind == "on_chat_model_stream":
                    text = _chunk_text(event["data"].get("chunk"))
                    if text:
                        cur_buf.append(text)
                elif kind == "on_chat_model_end":
                    output = event["data"].get("output")
                    tool_calls = getattr(output, "tool_calls", None) or []
                    if tool_calls:
                        # 工具决策步骤:记录轨迹并通知前端,其文本(通常为空)不输出
                        names = [n for n in (_tool_name(tc) for tc in tool_calls) if n]
                        if names:
                            trace.append({"step": "llm", "tool_calls": names})
                            yield _sse({"type": "tool_call", "tool": names})
                        cur_buf = []
                    else:
                        # 最终回答:把缓冲的 token 逐块输出
                        final_reply = _content_str(output) if output else "".join(cur_buf)
                        for piece in cur_buf:
                            yield _sse({"type": "token", "content": piece})
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    if hasattr(output, "content") and getattr(output, "content", None):
                        tool_outputs.append(str(output.content))
                    yield _sse({"type": "tool_done", "tool": event.get("name")})
    except GraphRecursionError:
        logger.warning("Agent 检索次数过多(user=%s),流式降级", user_id)
        yield _sse({"type": "error", "message": "检索次数过多未能找到答案，请换个问法或稍后再试。"})
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent 流式调用失败: %s", exc)
        yield _sse({"type": "error", "message": f"AI 服务调用失败: {exc}"})
        return

    final_reply = final_reply or "（无回复）"

    # Verifier 校验（可配置）：拿问题+答案+工具证据，grounded=false 时用校正后回复，done 帧携带校验信息
    verified = None
    if VERIFIER_ENABLED and final_reply:
        evidence = "\n".join(tool_outputs)[:4000]
        verified = await verifier_module.verify_answer(message, final_reply, evidence, user_memory=memory_ctx)
        if not verified["grounded"] and verified["corrected_reply"]:
            final_reply = verified["corrected_reply"]

    record = await ai_crud.add_chat(
        db, user_id, message, final_reply,
        session_id=session_id,
        agent_trace=trace,
    )
    # 记忆维护（fire-and-forget）：短期压缩 + 长期合并
    asyncio.create_task(memory_module.maybe_compress(user_id, session_id, llm))
    asyncio.create_task(consolidate_turn(user_id, session_id, message, final_reply))
    agent_logger.info(
        "[stream] 完成 user=%s session=%s reply=%d字符 trace=%s",
        user_id, session_id[:8], len(final_reply), trace,
        extra={"chat": {"event": "end", "stream": True, "user_id": user_id,
                        "session_id": session_id[:8], "reply_len": len(final_reply), "trace": trace}},
    )
    yield _sse({
        "type": "done",
        "chatId": record.id,
        "sessionId": session_id,
        "agentTrace": trace,
        "reply": final_reply,
        "createTime": record.created_at,
        "verified": verified,  # {"grounded", "corrected_reply", "note"}，可为 None（未启用/失败）
    })
