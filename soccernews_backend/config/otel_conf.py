"""OpenTelemetry 初始化：TracerProvider + 导出器（OTLP 或 Console）

日志可观测性升级（v1.2）：
- trace/span 全链路：HTTP(FastAPIInstrumentor) → agent.chat → agent.node → llm.call / tool.* / rag.*
- 日志通过 ContextFilter / OTelJsonFormatter 携带 trace_id/span_id（见 utils/log_context.py、config/logging_conf.py）

导出器选择（默认不导出，运行窗口保持纯彩色文本日志；日志仍带 trace_id/span_id）：
  - 设置 OTEL_EXPORTER_OTLP_ENDPOINT → 用 OTLP HTTP 导出到 Collector / Jaeger / Grafana（生产）
  - 设置 OTEL_TRACES_EXPORTER=console → Console 导出到 stdout（本地想直接看 span 树时用）
  - 设置 OTEL_TRACES_EXPORTER=none / 不设置 → 不导出（span 仍记录，但不打印到运行窗口）
"""
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

APP_SERVICE_NAME = "soccernews-backend"


def setup_otel() -> None:
    """初始化全局 TracerProvider（幂等：重复调用仅覆盖配置）

    默认不导出 span（运行窗口保持干净，只有彩色文本日志；日志仍带 trace_id/span_id）：
      - 设置 OTEL_EXPORTER_OTLP_ENDPOINT → OTLP HTTP 导出（生产）
      - 设置 OTEL_TRACES_EXPORTER=console → Console 导出到 stdout（本地看 span 树）
      - 设置 OTEL_TRACES_EXPORTER=none / 不设置 → 不导出
    """
    provider = TracerProvider(
        resource=Resource(attributes={SERVICE_NAME: APP_SERVICE_NAME})
    )
    exporter_name = os.getenv("OTEL_TRACES_EXPORTER", "").lower()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if endpoint or exporter_name == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    elif exporter_name == "console":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    # else：默认不挂 span processor —— span 仍记录（日志带 trace_id/span_id），但不导出到运行窗口

    trace.set_tracer_provider(provider)


# 全局 Tracer：Agent / LLM / RAG / Tool 手动 span 复用
# get_tracer 返回 ProxyTracer，setup_otel() 之后自动绑定已配置的 provider
tracer = trace.get_tracer("soccernews.backend")
