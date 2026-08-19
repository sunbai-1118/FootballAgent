"""足球头条资讯系统 后端入口"""
import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

import config
from agents import rag as agent_rag
from agents.embeddings import aclose_http_client
from config.cache_conf import init_cache,close_cache
from config.db_conf import engine
from config.logging_conf import setup_logging
from config.otel_conf import setup_otel
from routers import ai_chat, favorite, history, news, users
from utils.exception_handler import register_exception_handler
from utils.log_context import bind

setup_logging()  # 统一日志配置：控制台 + 文件按天 JSON 滚动
setup_otel()     # OpenTelemetry：TracerProvider + 导出器（trace/span 全链路）

request_logger = logging.getLogger("request")  # 请求日志专用 logger


# 应用生命周期管理
async def _maybe_index_on_startup() -> None:
    """启动后异步检查：RAG 向量库为空则自动重建索引（不阻塞启动）

    Qdrant / Docker 嵌入服务未就绪时仅记录告警，可用 POST /api/ai/rag/reindex 手动重建。
    """
    logger = logging.getLogger(__name__)
    try:
        if agent_rag.collection_size() == 0:
            count = await agent_rag.index_news()
            logger.info("启动自动索引完成：%d 个 point 写入 Qdrant", count)
        else:
            logger.info("RAG 索引已存在，跳过自动建索引")
    except Exception as exc:  # noqa: BLE001
        logger.warning("启动自动索引失败（可稍后通过 POST /api/ai/rag/reindex 重建）：%s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 Redis 并后台建 RAG 索引，关闭时释放资源"""
    await config.cache_conf.init_cache() #  初始化 Redis 连接（应用启动时调用）
    asyncio.create_task(_maybe_index_on_startup())  # 后台异步建 RAG 索引
    yield # 应用启动时执行
    await config.cache_conf.close_cache() # 应用关闭时执行
    await aclose_http_client()  # 释放嵌入服务 HTTP 连接
    await engine.dispose() # 数据库连接池关闭


# 创建 FastAPI 应用实例
app = FastAPI(
    title="足球头条资讯系统",
    description="基于 FastAPI 与 SQLAlchemy 构建的足球资讯系统后端 API，"
    "支持用户管理、足球资讯浏览、收藏与浏览历史功能",
    version="1.0.0",
    lifespan=lifespan,
)

# OpenTelemetry 自动埋点：置于最外层（先于 CORS/request_log 中间件），
# 保证 request_log 与后续所有 span（agent/llm/rag/tool）都挂在 http.request span 下、带同一 trace_id
FastAPIInstrumentor.instrument_app(app)

# 注册全局异常处理
register_exception_handler(app)

# CORS 跨域配置    同源才能前后端互通，同源需满足 协议 域名 端口 三者相同
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许的源，开发阶段允许所有源，生产阶段需要指定源
    allow_credentials=True,  #  允许携带cookie
    allow_methods=["*"], # 允许的 HTTP 方法
    allow_headers=["*"], # 允许的 HTTP 头
)


# 业务请求标识：接受前端 X-Request-Id（白名单字符 + 截断防注入）；真正的链路 id 是 OTel trace_id
_RE_ID = re.compile(r"[^A-Za-z0-9._-]")


# 请求日志中间件：记录方法/路径/状态码/耗时 + 结构化字段；异常也落日志后 re-raise
@app.middleware("http")
async def request_log(request, call_next):
    rid = _RE_ID.sub("", request.headers.get("X-Request-Id") or "")[:64]
    bind(request_id=rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        request_logger.exception(
            "%s %s -> 500 (%.1fms)",
            request.method, request.url.path, elapsed,
            extra={"request": {"method": request.method, "path": request.url.path, "status": 500,
                               "elapsed_ms": round(elapsed, 1),
                               "client": request.client.host if request.client else None}},
        )
        raise
    elapsed = (time.perf_counter() - start) * 1000
    request_logger.info(
        "%s %s -> %d (%.1fms)",
        request.method, request.url.path, response.status_code, elapsed,
        extra={"request": {"method": request.method, "path": request.url.path,
                           "status": response.status_code, "elapsed_ms": round(elapsed, 1),
                           "client": request.client.host if request.client else None}},
    )
    return response


# 统一异常处理：保证所有接口返回 {code, message, data} 结构
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数校验失败", "data": exc.errors()},
    )


# 1.3）注册各模块路由
app.include_router(users.router)
app.include_router(news.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(ai_chat.router)


@app.get("/", summary="服务健康检查")
async def root():
    return {"code": 200, "message": "足球头条资讯系统 API 运行中", "data": None}
