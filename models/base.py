"""全局共享 ORM 基类

所有模型统一继承此 Base，共享同一个 metadata / registry，
保证跨模块外键（如 favorite.user_id -> user.id）能正确解析。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

