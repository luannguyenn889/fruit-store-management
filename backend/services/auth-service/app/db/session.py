"""
Module: app.db.session
Nhiệm vụ: Khởi tạo kết nối cơ sở dữ liệu bất đồng bộ (SQLAlchemy 2.0 `AsyncEngine`
          và `async_sessionmaker`) tới `fruitstore_auth_db`, cung cấp dependency
          `get_db()` cho các route của Auth Service.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Cấu hình tham số pool phù hợp với PostgreSQL (hoặc SQLite khi chạy unit test cô lập)
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
    """Dependency cung cấp phiên làm việc bất đồng bộ (`AsyncSession`) cho mỗi request."""
    async with AsyncSessionLocal() as session:
        yield session

