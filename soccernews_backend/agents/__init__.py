"""Agent 核心层:LangGraph ReAct 智能体 + 多模态 RAG + 工具调用

每个 Agent 由 build_agent_graph 构建为可复用的 LangGraph 子图,
后续多 Agent(Supervisor)阶段可直接将子图作为 node 嵌入。
"""
