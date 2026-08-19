"""多模态 RAG:Qdrant 向量库(直接用 qdrant-client,命名向量 text / image)

设计要点:
- 检索单元 = 一条新闻(图文一体),图片不单独成 chunk;
- 每个 Qdrant point 挂两个命名向量:
    text  -> bge 文本向量(标题+简介+正文片段)
    image -> Chinese-CLIP 图片向量(该新闻封面图;无图填零向量 + has_image=false)
- 检索路径:
    retrieve_news   text→text  :问题 → bge  -> 搜 text 向量
    retrieve_images text→image :问题 → CLIP -> 搜 image 向量(仅 has_image=true)
"""
import logging
import time
import uuid
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

from agents.embeddings import embed_clip_images, embed_clip_text, embed_text
from agents.observability import _short
from config.db_conf import AsyncSessionLocal
from config.otel_conf import tracer
from config.rag_conf import (
    BGE_QUERY_PREFIX,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_DIM,
    QDRANT_COLLECTION,
    QDRANT_URL,
    RAG_TOP_K,
)
from crud import news as news_crud

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def _vector_config() -> dict[str, models.VectorParams]:
    """命名向量配置:text 与 image 均为 512 维余弦"""
    return {
        "text": models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
        "image": models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
    }


def ensure_collection() -> None:
    """collection 不存在则创建(启动时调用,不删除已有数据)"""
    client = _get_client()
    names = {c.name for c in client.get_collections().collections}
    if QDRANT_COLLECTION not in names:
        client.create_collection(QDRANT_COLLECTION, vectors_config=_vector_config())
        logger.info("已创建 Qdrant collection: %s", QDRANT_COLLECTION)


def collection_size() -> int:
    """当前向量库的点数(用于判断是否需要建索引)"""
    try:
        return _get_client().count(QDRANT_COLLECTION, exact=False).count
    except Exception:  # noqa: BLE001  collection 不存在等
        return 0


def _point_id(news_id: int, chunk_index: int) -> str:
    """确定性 point id(重索引不产生重复点):基于 news_id + chunk_index 的 UUID5"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"news:{news_id}:{chunk_index}"))


def _split_news(news, category_name: str | None, splitter) -> list[dict]:
    """把一条新闻切成若干图文 chunk(仅文本切片,图片向量在索引时统一编码)

    - 标题+简介不可分割,与正文首片放同一 chunk;
    - 正文用 RecursiveCharacterTextSplitter 按 CHUNK_SIZE/CHUNK_OVERLAP 切片;
    - 返回 [{"text": ..., "category": ...}, ...]
    """
    header = (news.title or "").strip()
    desc = (news.description or "").strip()
    if desc:
        header = f"{header}。{desc}"
    body = (news.content or "").strip()

    if body:
        parts = splitter.split_text(body) or []
        if parts:
            first = f"{header}。{parts[0]}" if header else parts[0]
            parts = [first] + parts[1:]
        else:
            parts = [header] if header else []
    else:
        parts = [header] if header else []

    return [{"text": p, "category": category_name} for p in parts if p]


async def index_news() -> int:
    """全量重建索引:读全部新闻 → 图文 chunk → 双命名向量 upsert(先删后建)

    返回写入的 point 数量。同步的 Qdrant 调用为阻塞操作,此处数据量不大(单机),
    后续量大可再包 asyncio.to_thread。
    """
    async with AsyncSessionLocal() as db:
        cats = await news_crud.get_categories(db)
        cat_map = {c.id: c.name for c in cats}
        rows = await news_crud.get_all_news(db)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    # 1) 预切片,并收集需要编码的图片 URL
    prepared: list[tuple[Any, list[dict]]] = []
    image_urls: list[str] = []
    for news in rows:
        chunks = _split_news(news, cat_map.get(news.category_id), splitter)
        if not chunks:
            continue
        prepared.append((news, chunks))
        if news.image:
            image_urls.append(news.image)

    # 2) 图片向量:URL 去重后分批调用(减少 HTTP 往返),失败位置为 None
    image_vec_map: dict[str, list[float] | None] = {}
    unique_urls = list(dict.fromkeys(image_urls))
    _IMG_BATCH = 8
    for i in range(0, len(unique_urls), _IMG_BATCH):
        batch = unique_urls[i:i + _IMG_BATCH]
        vecs = await embed_clip_images(batch)
        for url, vec in zip(batch, vecs):
            image_vec_map[url] = vec

    # 3) 组装 points(文本向量按条一次调用)
    points: list[models.PointStruct] = []
    for news, chunks in prepared:
        text_vecs = await embed_text([c["text"] for c in chunks])
        image_vec = image_vec_map.get(news.image) if news.image else None
        for i, chunk in enumerate(chunks):
            points.append(
                models.PointStruct(
                    id=_point_id(news.id, i),
                    vector={
                        "text": text_vecs[i],
                        "image": image_vec or [0.0] * EMBEDDING_DIM,  # 无图填零向量
                    },
                    payload={
                        "news_id": news.id,
                        "title": news.title,
                        "category": chunk["category"],
                        "publish_time": str(news.publish_time) if news.publish_time else None,
                        "image": news.image,
                        "has_image": image_vec is not None,
                        "chunk_index": i,
                    },
                )
            )

    client = _get_client()
    client.recreate_collection(QDRANT_COLLECTION, vectors_config=_vector_config())  # 先删后建
    if points:
        client.upsert(QDRANT_COLLECTION, points)
    logger.info("RAG 索引完成:共 %d 条新闻 -> %d 个 point", len(rows), len(points))
    return len(points)


async def retrieve_news(query: str, k: int = RAG_TOP_K) -> list[dict[str, Any]]:
    """text→text:问题加 bge 检索前缀 → bge 向量 → 搜 text 命名向量

    返回 payload 列表(含 news_id/title/category/image 等元数据)。
    """
    start = time.perf_counter()
    with tracer.start_as_current_span("rag.retrieve_news") as span:
        span.set_attributes({"rag.mode": "text->text", "rag.query": _short(query, 80), "rag.k": k})
        vec = (await embed_text([BGE_QUERY_PREFIX + query]))[0]
        hits = _get_client().query_points(
            collection_name=QDRANT_COLLECTION,
            query=vec,
            using="text",
            limit=k,
            with_payload=True,
        ).points
    elapsed_ms = (time.perf_counter() - start) * 1000
    max_score = max((h.score for h in hits), default=None)
    logger.info(
        "[rag] text 检索完成 k=%d hits=%d max_score=%s 耗时%.0fms",
        k, len(hits), max_score, elapsed_ms,
        extra={"rag": {"mode": "text->text", "query": _short(query, 80), "k": k,
                       "hits": len(hits), "max_score": max_score, "elapsed_ms": round(elapsed_ms, 1)}},
    )
    return [h.payload for h in hits]


async def retrieve_images(
    query: str, k: int = RAG_TOP_K, min_score: float | None = None
) -> list[dict[str, Any]]:
    """text→image:问题 → Chinese-CLIP 文本编码 → 搜 image 命名向量(仅 has_image=true)

    :param min_score: cosine 相似度阈值(0~1),低于该值的结果被过滤,避免返回不相关图片。
    """
    start = time.perf_counter()
    with tracer.start_as_current_span("rag.retrieve_images") as span:
        span.set_attributes({"rag.mode": "text->image", "rag.query": _short(query, 80),
                             "rag.k": k, "rag.min_score": min_score})
        vec = (await embed_clip_text([query]))[0]
        hits = _get_client().query_points(
            collection_name=QDRANT_COLLECTION,
            query=vec,
            using="image",
            query_filter=models.Filter(
                must=[models.FieldCondition(key="has_image", match=models.MatchValue(value=True))]
            ),
            limit=k,
            with_payload=True,
        ).points
    kept = [h for h in hits if min_score is None or h.score >= min_score]
    elapsed_ms = (time.perf_counter() - start) * 1000
    max_score = max((h.score for h in hits), default=None)
    logger.info(
        "[rag] image 检索完成 k=%d hits=%d kept=%d dropped=%d max_score=%s 耗时%.0fms",
        k, len(hits), len(kept), len(hits) - len(kept), max_score, elapsed_ms,
        extra={"rag": {"mode": "text->image", "query": _short(query, 80), "k": k,
                       "hits": len(hits), "kept": len(kept),
                       "dropped_by_min_score": len(hits) - len(kept),
                       "min_score": min_score, "max_score": max_score,
                       "elapsed_ms": round(elapsed_ms, 1)}},
    )
    return [h.payload for h in kept]
