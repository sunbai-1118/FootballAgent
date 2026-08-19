"""浏览历史相关数据库操作"""

from sqlalchemy import Row, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import History
from models.news import News


async def _touch_history(db: AsyncSession, history: History) -> History:
    """刷新已存在记录的浏览时间（置顶）"""
    await db.execute(
        update(History).where(History.id == history.id).values(view_time=func.now())
    )
    await db.commit()
    await db.refresh(history)
    return history


async def add_history(db: AsyncSession, user_id: int, news_id: int) -> History:
    """添加浏览记录：未浏览过则新增；已浏览过则刷新浏览时间（置顶），避免重复记录"""
    result = await db.execute(
        select(History).where(History.user_id == user_id, History.news_id == news_id)
    )
    history = result.scalar_one_or_none()
    if history:
        return await _touch_history(db, history)

    # 首次浏览：新增记录
    history = History(user_id=user_id, news_id=news_id)
    db.add(history)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # 并发下两条请求同时插入撞了唯一约束：改为更新已存在记录的浏览时间
        result = await db.execute(
            select(History).where(History.user_id == user_id, History.news_id == news_id)
        )
        history = result.scalar_one_or_none()
        if history:
            return await _touch_history(db, history)
        raise
    await db.refresh(history)
    return history


async def get_history_list(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10
) -> tuple[list[Row], int, bool]:
    """分页获取浏览历史列表（关联新闻信息），返回 (行, 总数, 是否还有更多)"""
    offset = (page - 1) * page_size
    count_result = await db.execute(
        select(func.count()).select_from(
            select(History.id).where(History.user_id == user_id).subquery()
        )
    )
    total = count_result.scalar() or 0

    # 显式选择 News 各列 + 历史记录ID/浏览时间，使 Row 顶层键与 schema 字段一一对应
    result = await db.execute(
        select(
            News.id, News.title, News.description, News.image, News.author,
            News.category_id, News.views, News.publish_time,
            History.id.label("history_id"),
            History.view_time.label("view_time"),
        )
        .join(News, History.news_id == News.id)
        .where(History.user_id == user_id)
        .order_by(History.view_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = list(result.all())
    has_more = offset + len(rows) < total
    return rows, total, has_more


async def delete_history(db: AsyncSession, user_id: int, history_id: int) -> int:
    """删除单条浏览记录（仅限本人），返回删除条数"""
    result = await db.execute(
        delete(History).where(History.id == history_id, History.user_id == user_id)
    )
    await db.commit()
    return result.rowcount or 0


async def clear_history(db: AsyncSession, user_id: int) -> int:
    """清空用户浏览历史，返回删除条数"""
    result = await db.execute(delete(History).where(History.user_id == user_id))
    await db.commit()
    return result.rowcount or 0
