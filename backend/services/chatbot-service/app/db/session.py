"""
Module: app.db.session (Chatbot Service)
Nhiệm vụ: Tạo `AsyncEngine`, `AsyncSessionLocal` và dependency `get_db`.
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Cung cấp AsyncSession cho mỗi request HTTP và tự động đóng sau khi xong."""
    async with AsyncSessionLocal() as session:
        yield session
