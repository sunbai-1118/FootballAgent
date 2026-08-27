"""API-Football 官方 Widget 数据反向代理。

浏览器访问本模块时不会接触 API Key；Key 只保留在后端环境变量
`API-FOOTBALL-API-KEY` 中，由这里注入到上游请求。
"""
import httpx
from fastapi import APIRouter, Request, Response

from config.football_conf import (
    API_FOOTBALL_BASE,
    API_FOOTBALL_KEY,
    API_FOOTBALL_TIMEOUT,
)

router = APIRouter(prefix="/widget-api/football", tags=["football-widgets"])

# 只开放 Widget 需要的只读数据端点。
ALLOWED_PREFIXES = ("fixtures", "standings", "leagues", "teams", "players")

# 官方脚本会读取这些响应头；缓存可降低免费套餐的请求消耗。
PASSTHROUGH_HEADERS = (
    "content-type",
    "cache-control",
    "etag",
    "expires",
    "last-modified",
)


@router.get("/{path:path}", summary="Football Widget read-only proxy")
async def proxy_football_widget(path: str, request: Request) -> Response:
    if not API_FOOTBALL_KEY:
        return Response(
            content='{"errors":{"proxy":"API-FOOTBALL key is not configured"}}',
            status_code=503,
            media_type="application/json",
        )
    clean_path = path.strip("/")
    if not any(clean_path == prefix or clean_path.startswith(f"{prefix}/") for prefix in ALLOWED_PREFIXES):
        return Response(status_code=404)

    # 丢弃客户端传入的 x-rapidapi-key / x-apisports-key，避免绕过或伪装。
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY,
        "accept": request.headers.get("accept", "application/json"),
    }
    params = dict(request.query_params.multi_items())

    async with httpx.AsyncClient(timeout=API_FOOTBALL_TIMEOUT) as client:
        upstream = await client.get(f"{API_FOOTBALL_BASE}/{clean_path}", headers=headers, params=params)

    response_headers = {
        key: value for key, value in upstream.headers.items() if key.lower() in PASSTHROUGH_HEADERS
    }
    response_headers.setdefault("Cache-Control", "public, max-age=30")
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
