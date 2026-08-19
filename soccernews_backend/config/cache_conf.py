"""Redis 缓存配置"""
import logging
import os

from redis import asyncio as aioredis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  #  本机
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))   #  默认端口
REDIS_DB = int(os.getenv("REDIS_DB", 0))         #  默认数据库
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  #  默认无密码

# 生成 Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# ==================== 缓存键模板（{} 由调用方填充） ====================
CACHE_KEY_NEWS_DETAIL = "news:detail:{}"                 # news:detail:{news_id}
CACHE_KEY_NEWS_LIST = "news:list:{}:{}:{}"               # news:list:{category_id}:{page}:{size}
CACHE_KEY_CATEGORIES = "news:categories"                 # 分类数据
CACHE_KEY_HISTORY_LIST = "history:list:{}:{}:{}"         # history:list:{user_id}:{page}:{size}

# ==================== 缓存过期时间（秒） ====================
CACHE_EXPIRE_NEWS_DETAIL = 3600      # 1 小时
CACHE_EXPIRE_NEWS_LIST = 1800        # 30 分钟
CACHE_EXPIRE_CATEGORIES = 7200       # 2 小时
CACHE_EXPIRE_HISTORY = 3600          # 1 小时

logger = logging.getLogger(__name__)

# 创建 Redis 连接对象
redis_client: aioredis.Redis | None = None


# 初始化 Redis 连接
async def init_cache() -> None:
    """初始化 Redis 连接（应用启动时调用）"""
    global redis_client
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        redis_client = client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 连接失败：%s，缓存功能将降级为直查数据库", exc)
        redis_client = None


# 关闭 Redis 连接
async def close_cache() -> None:
    """关闭 Redis 连接（应用关闭时调用）"""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
