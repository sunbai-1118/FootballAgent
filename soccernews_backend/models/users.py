"""用户与用户令牌 ORM 模型（对应 user / user_token 表）"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Index
from sqlalchemy.dialects.mysql import ENUM, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

# 2.定义模型类
class User(Base):
    """用户表"""
    __tablename__ = "user"

    # 创建索引
    __table_args__ = (
        Index("username_UNIQUE", "username"),
        Index("phone_UNIQUE", "phone"),
    )

# Optional 表示可选
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码（加密存储）")
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL")
    gender: Mapped[str] = mapped_column(
        ENUM("male", "female", "unknown"), default="unknown", server_default="unknown", comment="性别"
    )
    bio: Mapped[Optional[str]] = mapped_column(String(500), comment="个人简介")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment="手机号")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), server_onupdate=func.now(), comment="更新时间"
    )

    # 在控制台显示
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, nickname={self.nickname}, avatar={self.avatar}, gender={self.gender}, bio={self.bio}, phone={self.phone}, created_at={self.created_at}, updated_at={self.updated_at})>"


class UserToken(Base):
    """用户令牌表"""
    __tablename__ = "user_token"

    __table_args__ = (
        Index("token_UNIQUE", "token"),
        Index("fk_user_token_user_idx", "user_id"),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id}, token={self.token}, expires_at={self.expires_at}, created_at={self.created_at})>"
