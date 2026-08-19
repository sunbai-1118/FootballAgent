"""嵌入服务 HTTP 客户端

调用 Docker 内(见 docker/ 目录)的嵌入服务:
- text-embedding (bge-small-zh-v1.5):POST /embed/text -> 文本向量(text→text 检索)
- image-embedding (Chinese-CLIP):POST /embed/text 与 /embed/image -> 多模态向量(text→image 检索)
"""
import logging

import httpx

from config.rag_conf import (
    EMBED_TIMEOUT,
    EMBED_TIMEOUT_IMAGE,
    IMAGE_EMBEDDING_URL,
    TEXT_EMBEDDING_URL,
)

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """懒加载共享 AsyncClient(文本编码复用连接)"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=EMBED_TIMEOUT)
    return _client


async def aclose_http_client() -> None:
    """应用关闭时释放连接(lifespan 中调用)"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def embed_text(texts: list[str]) -> list[list[float]]:
    """bge 文本向量化(→ text→text 检索)"""
    r = await _get_client().post(f"{TEXT_EMBEDDING_URL}/embed/text", json={"texts": texts})
    r.raise_for_status()
    return r.json()["vectors"]


async def embed_clip_text(texts: list[str]) -> list[list[float]]:
    """Chinese-CLIP 文本编码(与图片同空间,→ text→image 检索)"""
    r = await _get_client().post(f"{IMAGE_EMBEDDING_URL}/embed/text", json={"texts": texts})
    r.raise_for_status()
    return r.json()["vectors"]


async def embed_clip_images(urls: list[str]) -> list[list[float] | None]:
    """Chinese-CLIP 图片编码;某个 URL 加载失败时对应位置返回 None(调用方填零向量降级)"""
    # 图片需远程加载 + 编码,单独使用更大的超时
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT_IMAGE) as client:
        r = await client.post(f"{IMAGE_EMBEDDING_URL}/embed/image", json={"images": urls})
    r.raise_for_status()
    return r.json()["vectors"]
