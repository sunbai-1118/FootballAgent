"""Redis 缓存工具：封装为独立函数便于调用，Redis 不可用时自动降级为直查数据库"""
import json
from typing import Any

from pydantic import BaseModel

import config.cache_conf as cache_conf
from config.cache_conf import logger


# 读取缓存并反序列化 JSON
async def get_cache(key: str) -> Any | None:
    """读取缓存并反序列化 JSON；未命中或异常返回 None"""
    if cache_conf.redis_client is None:
        return None
    try:
        value = await cache_conf.redis_client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 读取缓存 %s 失败：%s，将降级为直查数据库", key, exc)
        return None


# 写入缓存（JSON 序列化，Pydantic 模型 / datetime 自动转 JSON）
async def set_cache(key: str, value: Any, expire: int = 3600) -> None:
    """写入缓存（JSON 序列化，Pydantic 模型 / datetime 自动转 JSON）"""
    if cache_conf.redis_client is None:
        return
    try:
        if isinstance(value, BaseModel):
            # 先把 Pydantic 模型转成 JSON 可序列化字典（按别名，与接口响应一致）
            value = value.model_dump(mode="json", by_alias=True)
        await cache_conf.redis_client.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=expire)
    except Exception as exc:  # noqa: BLE001
        logger.warning("R   edis 设置缓存 %s 失败：%s，将降级为直写数据库", key, exc)
        return None



# 删除单个缓存键
async def delete_cache(key: str) -> None:
    """删除单个缓存键"""
    if cache_conf.redis_client is None:
        return
    try:
        await cache_conf.redis_client.delete(key)
    except Exception:  # noqa: BLE001
        pass


# 批量删除匹配模式的缓存键
async def delete_cache_pattern(pattern: str) -> None:
    """批量删除匹配模式的缓存键，如 news:list:*"""
    if cache_conf.redis_client is None:
        return
    try:
        keys = [key async for key in cache_conf.redis_client.scan_iter(match=pattern)]
        if keys:
            await cache_conf.redis_client.delete(*keys)
    except Exception:  # noqa: BLE001
        pass
