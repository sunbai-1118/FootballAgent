"""新闻相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.cache_conf import (
    CACHE_EXPIRE_CATEGORIES,
    CACHE_EXPIRE_NEWS_DETAIL,
    CACHE_EXPIRE_NEWS_LIST,
    CACHE_KEY_CATEGORIES,
    CACHE_KEY_NEWS_DETAIL,
    CACHE_KEY_NEWS_LIST,
)
from config.db_conf import get_db
from crud import news as news_crud
from utils.cache import delete_cache_pattern, get_cache, set_cache
from utils.response import success



# 创建APIRouter实例
# prefix: 路由前缀  tags: 路由分组标签
router = APIRouter(prefix="/api/news", tags=["新闻模块"])

#接口实现流程
#1.模块化路由 1）定义APIRouter实例  2） 创建路由  3）注册路由 4）参照API接口规范文档
#2.定义模型类 数据库表(数据库设计文档)
#3.在 crud 文件夹里面创建文件，封装操作数据库的方法
#4.在路由处理函数里面调用 crud 封装好的方法，响应结果

# 创建新闻分类路由
@router.get("/categories", summary="获取新闻分类列表")
# 获取新闻分类列表
async def get_categories(
    # 分页参数
    skip: int = Query(0, ge=0),  # 跳过前 n 个
    limit: int = Query(100, ge=1, le=100),  # 限制数量
    db: AsyncSession = Depends(get_db), # 数据库会话
):
    # 优先读缓存
    cached = await get_cache(CACHE_KEY_CATEGORIES)
    if cached is not None:
        return success(data=cached)
    # 调用 crud 封装好的方法，响应结果
    categories = await news_crud.get_categories(db, skip, limit)
    data = [
        {
            "id": c.id,
            "name": c.name,
            "sort_order": c.sort_order,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in categories  # 遍历分类列表
    ]
    # 前置虚拟「推荐」聚合频道（id 约定为 0，不落库）
    data.insert(0, {"id": 0, "name": "推荐", "sort_order": 0, "created_at": None, "updated_at": None})
    await set_cache(CACHE_KEY_CATEGORIES, data, CACHE_EXPIRE_CATEGORIES)  # 缓存分类列表
    return success(data=data)


# 新闻列表路由    # 获取新闻列表（分页 + 分类筛选）
@router.get("/list", summary="获取新闻列表（分页 + 分类筛选）")
async def get_news_list(
    category_id: int = Query(..., description="分类ID", alias="categoryId"),
    page: int = Query(1, ge=1, description="页码", alias="page"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量", alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    # 优先读缓存，缓存键为 CACHE_KEY_NEWS_LIST.format(category_id, page, page_size)
    cache_key = CACHE_KEY_NEWS_LIST.format(category_id, page, page_size)
    cached = await get_cache(cache_key)
    if cached is not None:
        return success(data=cached)
    # 内部辅助：构造新闻列表项（category 为分类名）
    def build_item(n, category_name):
        return {
            "id": n.id,
            "title": n.title,
            "description": n.description,
            "content": n.content,
            "image": n.image,
            "author": n.author,
            "category": category_name,
            "category_id": n.category_id,
            "views": n.views,
            "publish_time": n.publish_time,
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        }

    # 推荐频道（categoryId=0）：聚合各分类新闻，category 字段取各新闻真实分类名
    if category_id == 0:
        news_list, total, has_more = await news_crud.get_all_news_list(db, page, page_size)
        items = []
        for n in news_list:
            c = await news_crud.get_category_by_id(db, n.category_id)
            items.append(build_item(n, c.name if c else None))
    else:
        news_list, total, has_more = await news_crud.get_news_list(db, category_id, page, page_size)
        category = await news_crud.get_category_by_id(db, category_id)
        category_name = category.name if category else None
        items = [build_item(n, category_name) for n in news_list]

    data = {
        "list": items,
        "total": total,
        "hasMore": has_more,
    }
    await set_cache(cache_key, data, CACHE_EXPIRE_NEWS_LIST)
    return success(data=data)


# 新闻详情路由
@router.get("/detail", summary="获取新闻详情（浏览量 +1）")
async def get_news_detail(
    id: int = Query(..., description="新闻ID"),
    db: AsyncSession = Depends(get_db),
):
    news = await news_crud.get_news_detail(db, id)
    #  检查新闻是否存在
    if news is None:
        raise HTTPException(status_code=404, detail="新闻不存在")

    # 浏览量统计：每次浏览 +1，并刷新缓存
    news = await news_crud.increment_views(db, id)
    related = await news_crud.get_related_news(db, id)
    data = {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "image": news.image,
        "author": news.author,
        "publishTime": news.publish_time,
        "categoryId": news.category_id,
        "views": news.views,
        "relatedNews": [
            {
                "id": r.id,
                "title": r.title,
                "image": r.image,
                "publish_time": r.publish_time,
            }
            for r in related
        ],
    }
    await set_cache(CACHE_KEY_NEWS_DETAIL.format(id), data, CACHE_EXPIRE_NEWS_DETAIL)
    # 浏览量变化会影响列表展示，失效相关列表缓存
    await delete_cache_pattern("news:list:*")
    return success(data=data)
