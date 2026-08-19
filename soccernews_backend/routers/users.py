"""用户相关 API 路由"""
from http.client import responses

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import user

from config.db_conf import get_db
from crud import users as user_crud
from models.users import User
from schemas.users import PasswordUpdate, UserLogin, UserRegister, UserUpdate, UserAuthResponse, UserInFoResponse
from utils.auth import create_user_token, get_current_user, verify_password
from utils.response import success

# 1.1）创建APIRouter实例
router = APIRouter(prefix="/api/user", tags=["用户模块"])

_DEFAULT_BIO = "这个人很懒，什么都没留下"


# def _to_info(user: User) -> dict:
#     """用户信息返回结构"""
#     return {
#         "id": user.id,
#         "username": user.username,
#         "nickname": user.nickname,
#         "avatar": user.avatar,
#         "gender": user.gender or "unknown",
#         "bio": user.bio,
#     }

# 1.2）创建路由
# 用户注册路由
# 发送注册的POST请求 -->
# 检查用户名是否已存在（若已存在则返回错误） -->
# 创建用户（密码加密存储） -->
# 返回用户信息和token（生成访问令牌） -- >
# 响应结果
@router.post("/register", summary="用户注册")
async def register(data: UserRegister,db: AsyncSession = Depends(get_db)):
    if await user_crud.get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = await user_crud.create_user(db, data.username, data.password)
    token = await create_user_token(db, user.id)
    response_data = UserAuthResponse(token=token, userInfo=UserInFoResponse.model_validate(user))
    return success(
        data=response_data,
        message="注册成功",
    )

# 用户登录路由
# 发送登录的POST请求 -->
# 检查用户名是否已存在（若不存在则返回None） -->
# 验证密码(明文和密文)，若不一致则返回None -->
# 返回用户信息和token（生成访问令牌） -- >
# 响应结果
@router.post("/login", summary="用户登录")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await user_crud.authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = await create_user_token(db, user.id)
    response_data = UserAuthResponse(token=token, userInfo=UserInFoResponse.model_validate(user))
    return success(
        data=response_data,
        message="登录成功",
    )

# 获取用户信息路由
# 发送GET请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 查找对应用户（失败抛出异常）-->
# 响应结果
@router.get("/info", summary="获取用户信息")
async def get_info(user: User = Depends(get_current_user)):
    return success(
        data= UserInFoResponse.model_validate(user),
        message="获取成功",
    )

# 更新用户信息路由
# 发送PUT请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 检查用户是否存在（失败抛出异常） -->
# 更新用户信息（用户输入数据，put提交->请求体参数->定义pydantic模型类） -->
# 响应结果
@router.put("/update", summary="更新用户信息")
async def update_info(data: UserUpdate,current_user: User = Depends(get_current_user),db: AsyncSession = Depends(get_db),):
    user = await user_crud.update_user_info(db, current_user.username, data)
    return success(
        data=UserInFoResponse.model_validate(user),
        message="更新成功",
    )

# 修改用户密码路由
# 发送PUT请求 -->
# 检查令牌有效性（过期或者无令牌返回None） -->
# 检查用户是否登录（失败抛出异常） -->
# 验证原密码（不一致则返回错误） -->
# 修改用户密码（用户输入数据，put提交->请求体参数->定义pydantic模型类） 新密码转密文-->
# 更新密码
# 响应结果
@router.put("/password", summary="修改用户密码")
async def update_password(
    data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res_change_pwd = await user_crud.update_user_password(db, current_user, data.newPassword, data.oldPassword)
    if not res_change_pwd:
        raise HTTPException(status_code=400, detail="修改密码失败")
    return success(
        message="修改密码成功",
    )