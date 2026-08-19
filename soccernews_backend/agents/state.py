"""Agent 状态定义(LangGraph StateGraph 的共享状态)"""
from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 图的共享状态

    - messages: 对话消息,用 add_messages reducer 自动累积(含 AI 的 tool_calls 与工具返回)
    - agent_trace: 工具调用轨迹,便于落库与后续前端 SSE 过程可视化
    """
    messages: Annotated[list, add_messages]
    user_id: int                     # 会话用户,工具内做权限隔离
    session_id: Optional[str]
    agent_trace: list
