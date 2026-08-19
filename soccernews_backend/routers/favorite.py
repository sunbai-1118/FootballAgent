"""收藏相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud import favorite as fav_crud
from crud import news as news_crud
from models.users import User
from schemas.favorite import FavoriteAddRequest, FavoriteCheckResponse, FavoriteListData
from utils.auth import get_current_user
from utils.response import success

# 1.1）创建APIRouter实例
router = APIRouter(prefix="/api/favorite", tags=["收藏模块"])


# 1.2）创建路由

# 检查新闻收藏状态路由
#  发送GET请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 验证用户是否登录(未登录则抛出异常)->
# 检查用户是否已经收藏当前新闻->
# 响应结果
@router.get("/check", summary="检查新闻收藏状态")
async def check_favorite(
    news_id: int = Query(..., alias="newsId",description="新闻ID"),
   user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_fav = await fav_crud.is_favorite(db, user.id, news_id)
    return success(
        data=FavoriteCheckResponse(isFavorite=is_fav),
        message="检查收藏状态成功",
    )

# 添加收藏路由
#  发送POST请求 (请求体先定义pydantic模型类)-->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 验证用户是否登录(未登录则抛出异常)->
# 添加收藏->
# 响应结果
@router.post("/add", summary="添加收藏")
async def add_favorite(
    data: FavoriteAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = await fav_crud.add_favorite(db, user.id, data.news_id)
    return success(
        data=fav,
        message="添加收藏成功",
    )

# 取消收藏路由
#  发送DELETE请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 验证用户是否登录(未登录则抛出异常)->
# 取消收藏（删除收藏记录）->
# 检查命中数量是否大于0（不大于0抛出异常）->
# 响应结果
@router.delete("/remove", summary="取消收藏")
async def remove_favorite(
    news_id: int = Query(..., alias="newsId", description="新闻ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await fav_crud.remove_favorite(db, user.id, news_id)
    if not deleted:
        raise HTTPException(status_code=400, detail="尚未收藏该新闻")
    return success(message="取消收藏成功")

# 获取收藏列表路由
#  发送GET请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 验证用户是否登录(未登录则抛出异常)->
# 统计收藏的总量->
# 联表查询收藏新闻（用户、新闻信息）->
# 是否有更多数据->
# 响应结果
@router.get("/list", summary="获取收藏列表")
async def get_favorite_list(
    page: int = Query(1, ge=1, alias="page", description="页码"),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows, total, has_more = await fav_crud.get_favorite_list(db, user.id, page, page_size)
    data = FavoriteListData(list=rows, total=total, hasMore=has_more)
    return success(
        data=data,
        message="获取收藏列表成功",
    )

# 清空所有收藏路由
#  发送DELETE请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 验证用户是否登录(未登录则抛出异常)->
# 清空所有收藏（delete）->
# 响应结果
@router.delete("/clear", summary="清空所有收藏")
async def clear_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await fav_crud.clear_favorites(db, user.id)
    return success(message=f"清空了{count}条收藏记录")
