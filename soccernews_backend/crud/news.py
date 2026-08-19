"""新闻相关数据库操作"""
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import News, NewsCategory, RelatedNews


# 封装查询数据的方法
async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[NewsCategory]:
    """获取新闻分类列表（按 sort_order 升序）"""
    result = await db.execute(
        select(NewsCategory).order_by(NewsCategory.sort_order.asc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())

# 封装按ID查询分类的方法
async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[NewsCategory]:
    """按分类ID查询分类"""
    result = await db.execute(select(NewsCategory).where(NewsCategory.id == category_id))
    return result.scalar_one_or_none()

# 封装分页查询新闻列表的方法
async def get_news_list(db: AsyncSession, category_id: int, page: int = 1, page_size: int = 10) -> Tuple[List[News], int, bool]:
    """分页获取指定分类的新闻列表，返回 (列表, 总数, 是否还有更多)"""
    offset = (page - 1) * page_size
    base = select(News).where(News.category_id == category_id)
    # 查询总数
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0
    # 查询新闻列表
    result = await db.execute(
        base.order_by(News.publish_time.desc(), News.id.desc()).offset(offset).limit(page_size)
    )
    news_list = list(result.scalars().all())
    has_more = offset + len(news_list) < total
    return news_list, total, has_more


# 封装分页查询全部新闻列表的方法（「推荐」聚合频道使用，不按分类过滤）
async def get_all_news_list(db: AsyncSession, page: int = 1, page_size: int = 10) -> Tuple[List[News], int, bool]:
    """分页获取全部新闻列表（各分类混合、按最新优先），返回 (列表, 总数, 是否还有更多)"""
    offset = (page - 1) * page_size
    base = select(News)
    # 查询总数
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0
    # 查询新闻列表
    result = await db.execute(
        base.order_by(News.publish_time.desc(), News.id.desc()).offset(offset).limit(page_size)
    )
    news_list = list(result.scalars().all())
    has_more = offset + len(news_list) < total
    return news_list, total, has_more

# 封装按关键词搜索新闻的方法(Agent 工具使用)
async def search_news(db: AsyncSession, keyword: str, limit: int = 5) -> List[News]:
    """关键词搜索:标题或内容 LIKE 模糊匹配,按发布时间倒序"""
    like = f"%{keyword}%"
    result = await db.execute(
        select(News)
        .where(or_(News.title.like(like), News.content.like(like)))
        .order_by(News.publish_time.desc(), News.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# 封装获取热门新闻的方法(Agent 工具使用)
async def get_hot_news(db: AsyncSession, limit: int = 5) -> List[News]:
    """热门新闻:按浏览量倒序"""
    result = await db.execute(
        select(News)
        .order_by(News.views.desc(), News.publish_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# 封装获取全部新闻的方法(Agent RAG 索引用,不分页)
async def get_all_news(db: AsyncSession) -> List[News]:
    """全部新闻(不分页,供向量索引全量重建)"""
    result = await db.execute(select(News))
    return list(result.scalars().all())


# 封装按ID查询新闻详情的方法
async def get_news_detail(db: AsyncSession, news_id: int) -> Optional[News]:
    """按ID查询新闻详情"""
    result = await db.execute(select(News).where(News.id == news_id))
    return result.scalar_one_or_none()

# 封装浏览量 +1 的方法
async def increment_views(db: AsyncSession, news_id: int) -> Optional[News]:
    """浏览量 +1，返回更新后的新闻"""
    news = await get_news_detail(db, news_id)
    #  如果新闻不存在则返回 None
    if news is None:
        return None
    #  更新浏览量
    news.views = (news.views or 0) + 1
    #  提交事务
    await db.commit()
    await db.refresh(news)
    return news

# 封装按新闻ID查询相关新闻的方法
async def get_related_news(db: AsyncSession, news_id: int, limit: int = 3) -> List[News]:
    """获取相关新闻（最多 limit 条）"""
    result = await db.execute(
        select(News)
        .join(RelatedNews, RelatedNews.related_news_id == News.id)
        .where(RelatedNews.news_id == news_id)
        .order_by(News.views.desc(), News.publish_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
