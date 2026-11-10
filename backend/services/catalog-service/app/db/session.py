"""
Module: app.db.session (Catalog Service)
Nhiệm vụ: Quản lý kết nối cơ sở dữ liệu bất đồng bộ (`AsyncEngine` và `async_sessionmaker`)
          tới `fruitstore_catalog_db` hoàn toàn độc lập với các service khác (NFR-S08).
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

engine_kwargs = {"echo": False}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency cung cấp `AsyncSession` kết nối tới `fruitstore_catalog_db`."""
    async with AsyncSessionLocal() as session:
        yield session

