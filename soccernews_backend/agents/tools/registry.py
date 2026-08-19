"""工具注册表:统一登记、按名查询

为多 Agent 预留:未来 Supervisor 可聚合所有子 Agent 的工具集。
"""
from langchain_core.tools import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_many(self, *tools: BaseTool) -> "ToolRegistry":
        for t in tools:
            self._tools[t.name] = t
        return self

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)
