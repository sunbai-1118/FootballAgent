"""收藏相关数据库操作"""
from datetime import datetime
from typing import List, Tuple, Any, Coroutine

from sqlalchemy import delete, func, select, Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.favorite import Favorite
from models.news import News

# 3.封装用户相关数据库操作

# 检查新闻收藏状态
async def is_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """检查用户是否已收藏某新闻"""
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    )
    # 是否有收藏记录
    return result.scalar_one_or_none() is not None

# 添加收藏
async def add_favorite(db: AsyncSession, user_id: int, news_id: int) -> Favorite:
    """添加收藏（已收藏则幂等返回，避免唯一约束冲突报错）"""
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    fav = Favorite(user_id=user_id, news_id=news_id)
    db.add(fav)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # 并发重复请求：返回已存在的收藏记录
        result = await db.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
        )
        return result.scalar_one_or_none()
    await db.refresh(fav) # 刷新fav对象，使其包含数据库生成的最新的字段值
    return fav

# 取消收藏
async def remove_favorite(db: AsyncSession, user_id: int, news_id: int) -> int:
    """取消收藏，返回删除条数"""
    result = await db.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    )
    await db.commit()
    # 是否有删除记录，为True表示删除成功   为False表示无删除记录返回异常
    return result.rowcount > 0

# 获取收藏列表
async def get_favorite_list(db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10) -> tuple[list[Row[tuple[News, datetime, int]]], Any, bool | Any]:

    # 查询总量
    count_result = await db.execute(select(func.count(Favorite.id)).where(Favorite.user_id == user_id))
    total = count_result.scalar_one()

    # 获取收藏的新闻列表
    offset = (page - 1) * page_size
    # 联合查询：显式选择 News 各列 + 收藏时间/收藏ID，
    # 使返回的 Row 顶层键与 schema 字段一一对应，便于 Pydantic from_attributes 取值
    result = await db.execute(
        select(
            News.id, News.title, News.description, News.image, News.author,
            News.category_id, News.views, News.publish_time,
            Favorite.created_at.label("favorite_time"),
            Favorite.id.label("favorite_id"),
        )
        .join(Favorite, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    # 获取结果
    rows = list(result.all())
    # 是否还有更多
    has_more = offset + len(rows) < total
    # 返回结果
    return rows, total, has_more

# 清空收藏列表
async def clear_favorites(db: AsyncSession, user_id: int) -> int:
    """清空用户所有收藏，返回删除条数"""
    result = await db.execute(delete(Favorite).where(Favorite.user_id == user_id))
    await db.commit()
    # 返回删除的数量
    return result.rowcount or 0
