"""数据库配置：创建异步引擎与会话工厂（ORM 基类见 models/news.py）

连接参数通过环境变量 / .env 配置（示例见 .env.example 的 DB_*），不硬编码密码。
"""
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()  # 加载项目根目录 .env 文件（若存在）

# ==================== 数据库连接配置（走环境变量，避免提交密钥） ====================
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")  # TODO: 生产请通过 .env 配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "news_app")

# 数据库URL
DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# SQLAlchemy echo 日志（每条 SQL 打印到 stderr，开发调试用，默认关闭避免刷屏；需要时设环境变量 DB_ECHO=true）
DB_ECHO = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")

# 创建异步引擎（连接池）
engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,             # 默认关闭，见上方 DB_ECHO
    pool_size=10,              # 连接池大小
    max_overflow=20,           # 连接池最大溢出数
    pool_recycle=3600,         # 连接池回收时间
    pool_pre_ping=True,        # 可选：是否预ping 意思是每次获取连接时都进行ping
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db():
    """FastAPI 依赖：提供数据库会话（每个请求独立事务）"""
    async with AsyncSessionLocal() as session:
        yield session


# async def init_db():
#     """初始化数据库表（开发环境自动建表，生产建议直接导入 database.sql）"""
#     from models.news import Base
#     import models  # noqa: F401  确保所有模型已注册到 Base.metadata
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)