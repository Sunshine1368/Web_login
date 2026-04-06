"""
app/database.py - 异步数据库引擎与会话工厂
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# 创建异步引擎
# SQLite 需要 check_same_thread=False，PostgreSQL 则直接用 asyncpg
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass
