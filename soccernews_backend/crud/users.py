"""用户相关数据库操作"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.users import UserUpdate
from utils.auth import hash_password, verify_password

# 3.封装用户相关数据库操作

# 按用户名查询用户
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()

# 按用户ID查询用户
async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# 创建新用户（密码加密存储）
async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    nickname: Optional[str] = None,
    avatar: Optional[str] = None,
) -> User:
    user = User(
        username=username,
        password=hash_password(password),
        nickname=nickname,
        avatar=avatar,
    )
    db.add(user)  # 添加用户到会话
    await db.commit()  #  提交事务
    await db.refresh(user)  # 从数据库读回最新的user
    return user

# 校验用户名和密码，成功返回用户，失败返回 None
async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """校验用户名和密码，成功返回用户，失败返回 None"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if user is None or not verify_password(password, user.password):
        return None
    return user

# 更新用户信息 : update更新 -> 检查是否命中 -> 获取更新后的用户
async def update_user_info(db: AsyncSession, username: str, user_data: UserUpdate) -> User:
    # update(User).where(User.username == username).values(字段=值，字段=值)
    # update 是一个pydantic类型，得到字典 -> **解包
    # 没有设置的值不更新
    query = update(User).where(User.username == username).values(**user_data.model_dump(
        exclude_unset=True,
        exclude_none=True
    ))
    result = await db.execute(query)
    await db.commit()

    # 检查更新
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取一下更新的用户
    updated_user = await get_user_by_username(db, username)
    return updated_user

# 修改用户密码 ： 验证旧密码 -> 新密码加密 -> 修改密码
async def update_user_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> bool:
    # 验证旧密码
    if not verify_password(old_password, user.password):
        return False

    # 新密码加密
    user.password = hash_password(new_password)

    # 更新:由SQLAlchemy真正接管这个User 对象，确保可以 commit
    # 规避 session过期或关闭导致的不能提交的问题
    db.add(user)

    await db.commit()
    await db.refresh(user)
    return True




