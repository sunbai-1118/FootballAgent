"""浏览历史相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.cache_conf import (
    CACHE_EXPIRE_HISTORY,
    CACHE_KEY_HISTORY_LIST,
)
from config.db_conf import get_db
from crud import history as history_crud
from crud import news as news_crud
from models.users import User
from schemas.history import HistoryAdd, HistoryListData
from utils.auth import get_current_user
from utils.cache import delete_cache_pattern, get_cache, set_cache
from utils.response import success

router = APIRouter(prefix="/api/history", tags=["浏览历史模块"])

# 添加浏览记录路由
@router.post("/add", summary="添加浏览记录")
async def add_history(
    data: HistoryAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    #   检查新闻是否存在
    if await news_crud.get_news_detail(db, data.newsId) is None:
        raise HTTPException(status_code=404, detail="新闻不存在")

    #   添加浏览记录（已浏览过会刷新浏览时间，不重复插入）
    history = await history_crud.add_history(db, user.id, data.newsId)
    # 失效该用户的历史缓存
    await delete_cache_pattern(CACHE_KEY_HISTORY_LIST.format(user.id, "*", "*"))
    return success(
        data=HistoryListData(id=history.id, viewTime=history.view_time),
        message="添加成功",
    )

# 获取浏览历史列表路由
@router.get("/list", summary="获取浏览历史列表")
async def get_history_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize",description="每页数量"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = CACHE_KEY_HISTORY_LIST.format(user.id, page, page_size)
    cached = await get_cache(cache_key)
    if cached is not None:
        return success(data=cached, message="获取浏览历史列表成功")

    rows, total, has_more = await history_crud.get_history_list(db, user.id, page, page_size)
    data = HistoryListData(list=rows, total=total, hasMore=has_more )
    await set_cache(cache_key, data, CACHE_EXPIRE_HISTORY)
    return success(
        data=data,
        message="获取浏览历史列表成功",
    )

# 删除单条浏览记录路由
@router.delete("/delete/{history_id}", summary="删除单条浏览记录")
async def delete_history(
    history_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await history_crud.delete_history(db, user.id, history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    await delete_cache_pattern(CACHE_KEY_HISTORY_LIST.format(user.id, "*", "*"))
    return success(message="删除浏览记录成功")

# 清空浏览历史路由
@router.delete("/clear", summary="清空浏览历史")
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await history_crud.clear_history(db, user.id)
    await delete_cache_pattern(CACHE_KEY_HISTORY_LIST.format(user.id, "*", "*"))
    return success(message="清空浏览记录成功")
