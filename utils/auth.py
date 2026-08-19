"""认证与密码工具：密码加密、令牌生成与验证"""
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.users import User, UserToken
from utils.log_context import bind

# 令牌有效期：7 天
TOKEN_EXPIRE_DAYS = 7

# 创建密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 密码加密
def hash_password(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

# 密码校验
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    return pwd_context.verify(plain_password, hashed_password)

# 生成随机令牌
def generate_token() -> str:
    """生成随机访问令牌"""
    return secrets.token_urlsafe(32)

# 生成token
async def create_user_token(db: AsyncSession, user_id: int) -> str:
    """为用户创建访问令牌（有效期 7 天）"""
    token = generate_token()
    expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)
    db.add(UserToken(user_id=user_id, token=token, expires_at=expires_at))
    await db.commit()
    return token

# 通过令牌（token）获取用户
async def get_user_by_token(db: AsyncSession, token: str):
    """通过令牌获取用户（令牌需未过期）"""
    result = await db.execute(
        select(UserToken).where(
            UserToken.token == token,
            UserToken.expires_at > datetime.now(),  # 令牌未过期
        )
    )
    user_token = result.scalar_one_or_none()

    # 如果令牌不存在或者令牌已过期
    if user_token is None:
        return None
    result = await db.execute(select(User).where(User.id == user_token.user_id))
    return result.scalar_one_or_none()

# 整合  根据token查询用户  返回用户
async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI 依赖：从 Authorization 请求头解析当前登录用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    user = await get_user_by_token(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    bind(user_id=user.id)  # 登录接口的后续日志（agent/graph/llm/rag/tool）带 user_id
    return user
