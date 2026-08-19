"""LangGraph ReAct 图构建

图结构:
    START -> agent(LLM 决策) --有 tool_calls--> tools(ToolNode 执行) -> 回到 agent
                     └----无 tool_calls----> END

多 Agent 扩展:此函数返回的图可作为 node 嵌入 Supervisor 图。
"""
import time

from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from agents.observability import logger as agent_logger
from agents.prompts import build_system_prompt
from agents.state import AgentState
from config.otel_conf import tracer

# 单次对话内工具调用次数上限：超过则强制 agent 停止检索、直接给结论（防无限工具循环）
MAX_TOOL_CALLS = 8


def build_agent_graph(llm, tools: list[BaseTool], memory_context: dict | None = None) -> CompiledStateGraph:
    """构建单 Agent ReAct 子图

    :param llm: 已配置的对话模型(来自 LLMFactory)
    :param tools: 工具列表(来自 ToolRegistry)
    :param memory_context: 记忆上下文(长期记忆/会话摘要/关键事实)，由 _prepare 加载后以**闭包**注入，
                           不放进 AgentState（工作记忆只承载单轮 ReAct 状态）
    """
    llm_with_tools = llm.bind_tools(tools)

    async def agent_node(state: AgentState) -> dict:
        # 取最近一段消息,避免上下文无限膨胀
        recent = state["messages"][-20:]
        # 系统提示词动态注入当前日期 + 记忆上下文（闭包传入，不经过 AgentState）
        messages = [{"role": "system", "content": build_system_prompt(memory_context)}, *recent]
        # 循环检测：统计已发生的工具调用次数，超上限则强制停止检索、直接给结论
        tool_calls_so_far = sum(
            1 for m in state["messages"]
            if getattr(m, "type", "") == "ai" and getattr(m, "tool_calls", None)
        )
        if tool_calls_so_far >= MAX_TOOL_CALLS:
            messages.append({
                "role": "system",
                "content": "你已经调用了很多次工具仍未获得答案。请立即停止调用任何工具，"
                           "直接基于已获得的工具结果组织最终回答；若确实没有答案，如实说明查不到。",
            })
        node_start = time.perf_counter()
        agent_logger.info(
            "[graph] agent 开始 messages=%d",
            len(recent),
            extra={"graph": {"event": "node_start", "messages": len(recent),
                             "user_id": state.get("user_id"), "session_id": state.get("session_id")}},
        )
        # 用 astream 收集分片:既得到完整回复,也让外层 astream_events 产生 token 级流式事件
        with tracer.start_as_current_span("agent.node") as span:
            span.set_attribute("user_id", state.get("user_id"))
            chunks: list = []
            async for chunk in llm_with_tools.astream(messages):
                chunks.append(chunk)
            resp = chunks[0] if chunks else await llm_with_tools.ainvoke(messages)
            for c in chunks[1:]:
                resp = resp + c  # AIMessageChunk.__add__ 合并 content 与 tool_calls
        elapsed_ms = (time.perf_counter() - node_start) * 1000
        trace = list(state.get("agent_trace") or [])
        usage = getattr(resp, "usage_metadata", None) or {}
        if getattr(resp, "tool_calls", None):
            names = [
                c.get("name") if isinstance(c, dict) else getattr(c, "name", None)
                for c in resp.tool_calls
            ]
            agent_logger.info(
                "[graph] agent 决策调用工具: %s",
                names,
                extra={"graph": {"event": "decision", "tools": names,
                                 "elapsed_ms": round(elapsed_ms, 1),
                                 "total_tokens": usage.get("total_tokens")}},
            )
            trace.append({"step": "llm", "tool_calls": names})
        else:
            content = getattr(resp, "content", "")
            reply_len = len(content) if isinstance(content, str) else 0
            agent_logger.info(
                "[graph] agent 结束(最终回答) reply=%d字符 耗时%.0fms",
                reply_len, elapsed_ms,
                extra={"graph": {"event": "final_answer", "reply_len": reply_len,
                                 "elapsed_ms": round(elapsed_ms, 1),
                                 "total_tokens": usage.get("total_tokens")}},
            )
        return {"messages": [resp], "agent_trace": trace}

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))  # 自动执行 tool_calls 并把结果作为 ToolMessage 回填
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # 工具结果回到 agent 继续决策(由 recursion_limit 兜底)
    return graph.compile()
