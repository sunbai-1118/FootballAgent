"""请求级日志上下文：user_id / session_id / request_id + OTel trace 注入

trace_id/span_id 由 OpenTelemetry 提供（config/otel_conf.py），这里只维护业务上下文，
并通过 ContextFilter 统一写入 LogRecord，供控制台文本前缀与 JSON 结构化日志使用。

使用示例：
    from utils.log_context import bind, get_context
    bind(user_id=1, session_id="xxx")          # 在路由依赖 / agent_service 里绑定
    logging.getLogger(...).info("...", extra={"section": {...}})
"""
import contextvars
import logging

from opentelemetry.trace import format_span_id, format_trace_id, get_current_span

_user_id_var: contextvars.ContextVar = contextvars.ContextVar("user_id", default=None)
_session_id_var: contextvars.ContextVar = contextvars.ContextVar("session_id", default="")
_request_id_var: contextvars.ContextVar = contextvars.ContextVar("request_id", default="")


def bind(
    user_id: int | str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """在请求上下文里绑定业务标识（仅 set 非 None 的）"""
    if user_id is not None:
        _user_id_var.set(user_id)
    if session_id is not None:
        _session_id_var.set(session_id)
    if request_id is not None:
        _request_id_var.set(request_id)


def get_context() -> dict:
    """供 JSON 日志的 context 字段使用"""
    return {
        "user_id": _user_id_var.get(),
        "session_id": _session_id_var.get(),
        "request_id": _request_id_var.get(),
    }


def reset() -> None:
    """后台任务 / 测试显式清理"""
    _user_id_var.set(None)
    _session_id_var.set("")
    _request_id_var.set("")


class ContextFilter(logging.Filter):
    """挂到 console/file handler：把 OTel trace + 业务上下文写入 LogRecord

    - record.trace_id / span_id / trace_id_short：来自当前 OTel span
    - record.user_id / session_id / request_id / context：来自 contextvars
    - record.trace_prefix：有 trace 时为 "[tid8] "，无 trace 为空串（控制台不显示空的 []）
    """

    def filter(self, record: logging.LogRecord) -> bool:
        span = get_current_span()
        sc = span.get_span_context() if span is not None else None
        if sc is not None and sc.is_valid:
            record.trace_id = format_trace_id(sc.trace_id)
            record.span_id = format_span_id(sc.span_id)
            record.trace_id_short = record.trace_id[:8]
            record.trace_prefix = f"[{record.trace_id_short}] "
        else:
            record.trace_id = ""
            record.span_id = ""
            record.trace_id_short = ""
            record.trace_prefix = ""
        record.user_id = _user_id_var.get()
        record.session_id = _session_id_var.get()
        record.request_id = _request_id_var.get()
        record.context = {
            "user_id": record.user_id,
            "session_id": record.session_id,
            "request_id": record.request_id,
        }
        return True
