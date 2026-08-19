"""Agent 可观测性：LLM 调用日志 + Tool 调用日志（OTel span + 结构化字段）

日志通过 logger 名 "agent" 输出，经根 logger 传播到控制台 + logs/app-*.log（见 config/logging_conf.py）。
trace_id/span_id 由 OpenTelemetry 提供（config/otel_conf.py），经 ContextFilter 写入每条日志。

多模型适配：模型名从 langchain serialized 通用提取、token 用量取 langchain usage_metadata，
因此更换/新增 provider（DeepSeek / Claude / DashScope…）无需改本文件。
"""
import functools
import logging
import time
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from opentelemetry.trace import Status, StatusCode

from config.otel_conf import tracer

logger = logging.getLogger("agent")


def _short(value, limit: int = 200) -> str:
    """截断并压平长文本，便于日志单行可读"""
    s = str(value).replace("\n", " ").strip()
    return s if len(s) <= limit else s[:limit] + f"...(共{len(s)}字符)"


def _extract_model_name(serialized: dict | None, fallback: str | None = None) -> str:
    """从 langchain serialized 信息里通用提取模型名（适配任意 provider 的 chat model）"""
    if not serialized:
        return fallback or ""
    kwargs = serialized.get("kwargs") or {}
    for key in ("model", "model_name", "model_id", "name"):
        val = kwargs.get(key) or serialized.get(key)
        if val:
            return str(val)
    return fallback or ""


def log_tool_call(func):
    """工具调用日志装饰器：OTel span（tool.<name>）+ 结构化日志（工具名/入参/结果长度/耗时/成败）

    用法：装饰在 @tool 工具函数上，保持 @log_tool_call 在下层：
        @tool
        @log_tool_call
        async def my_tool(...): ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            with tracer.start_as_current_span(f"tool.{func.__name__}") as span:
                span.set_attribute("tool.name", func.__name__)
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                summary = result if isinstance(result, str) else str(result)
                span.set_attributes({"tool.result_len": len(summary), "tool.elapsed_ms": round(elapsed_ms, 1)})
        except Exception as exc:  # noqa: BLE001
            # start_as_current_span 的 __exit__ 已自动 record_exception + ERROR 状态
            logger.warning(
                "[tool] %s 异常: %s", func.__name__, exc,
                exc_info=True,  # JSON 日志含 exception 字段
                extra={"tool": {"name": func.__name__, "args": _short(args or kwargs, 120),
                                "elapsed_ms": round((time.perf_counter() - start) * 1000, 1), "ok": False}},
            )
            raise
        logger.info(
            "[tool] %s args=%s -> %d字符 耗时%.0fms",
            func.__name__, _short(args or kwargs, 120), len(summary), elapsed_ms,
            extra={"tool": {"name": func.__name__, "args": _short(args or kwargs, 120),
                            "result_len": len(summary), "elapsed_ms": round(elapsed_ms, 1), "ok": True}},
        )
        return result

    return wrapper


class LLMLoggingHandler(BaseCallbackHandler):
    """通用 LLM 调用可观测：OTel span（llm.call）+ 结构化日志（provider 无关）

    必须全部 async 方法：同步回调会被 LangChain 丢进线程池，导致 contextvars/OTel 上下文丢失。
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._start: dict[UUID, float] = {}    # run_id -> perf_counter
        self._tokens: dict[UUID, int] = {}     # run_id -> 累计流式 token
        self._spans: dict[UUID, object] = {}   # run_id -> OTel span

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs) -> None:
        model = _extract_model_name(serialized, self.model_name)
        if self.model_name is None:
            self.model_name = model
        span = tracer.start_span(
            "llm.call",
            attributes={"llm.model": model, "llm.messages": len(messages[0]) if messages else 0},
        )
        self._start[run_id] = time.perf_counter()
        self._spans[run_id] = span
        logger.debug("[llm] 开始 model=%s", model)

    async def on_llm_new_token(self, token, *, run_id, **kwargs) -> None:
        # 只累计不逐 token 打日志（流式会触发很多次；末尾空 token 不计入）
        if token:
            self._tokens[run_id] = self._tokens.get(run_id, 0) + 1

    async def on_llm_end(self, response: LLMResult, *, run_id, **kwargs) -> None:
        span = self._spans.pop(run_id, None)
        elapsed_ms = (time.perf_counter() - self._start.pop(run_id, time.perf_counter())) * 1000
        gen = response.generations[0][0] if response.generations else None
        msg = getattr(gen, "message", None)
        tool_calls = getattr(msg, "tool_calls", None) or []
        names = [c.get("name") if isinstance(c, dict) else getattr(c, "name", "") for c in tool_calls]
        usage = getattr(msg, "usage_metadata", None) or {}
        reply_len = len(msg.content) if getattr(msg, "content", None) else 0
        if span is not None:
            attrs = {
                "llm.tool_calls": ",".join(names),
                "llm.input_tokens": usage.get("input_tokens"),
                "llm.output_tokens": usage.get("output_tokens"),
                "llm.total_tokens": usage.get("total_tokens"),
                "llm.elapsed_ms": round(elapsed_ms, 1),
            }
            span.set_attributes({k: v for k, v in attrs.items() if v is not None})
            span.end()
        logger.info(
            "[llm] 完成 model=%s tool_calls=%s tokens=%d elapsed=%.0fms",
            self.model_name or "", names, usage.get("total_tokens") or 0, elapsed_ms,
            extra={"llm": {"event": "end",
                           "model": self.model_name or "",
                           "tool_calls": names,
                           "input_tokens": usage.get("input_tokens"),
                           "output_tokens": usage.get("output_tokens"),
                           "total_tokens": usage.get("total_tokens"),
                           "stream_tokens": self._tokens.pop(run_id, 0),
                           "elapsed_ms": round(elapsed_ms, 1),
                           "reply_len": reply_len}},
        )

    async def on_llm_error(self, error, *, run_id, **kwargs) -> None:
        span = self._spans.pop(run_id, None)
        elapsed_ms = (time.perf_counter() - self._start.pop(run_id, time.perf_counter())) * 1000
        if span is not None:
            span.set_attribute("llm.elapsed_ms", round(elapsed_ms, 1))
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.end()
        logger.warning(
            "[llm] 异常: %s", error,
            exc_info=error,  # exc_info 接受异常实例，JSON 日志含 exception 字段
            extra={"llm": {"event": "error", "elapsed_ms": round(elapsed_ms, 1)}},
        )
