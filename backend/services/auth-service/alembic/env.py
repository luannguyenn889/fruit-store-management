"""
Module: alembic.env (Auth Service)
Nhiệm vụ: Thiết lập môi trường chạy migration bất đồng bộ (AsyncEngine) cho Alembic,
          tự động lấy `DATABASE_URL` từ `app.core.config.settings` và `Base.metadata`
          từ `app.models`.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 - Nạp đầy đủ các model vào Base.metadata

config = context.config

# Ghi đè sqlalchemy.url bằng DATABASE_URL thực tế từ biến môi trường / .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline (chỉ xuất SQL, không cần kết nối DB trực tiếp)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Hàm callback thực thi migration trên kết nối đồng bộ được bọc bởi AsyncEngine."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Khởi tạo AsyncEngine và chạy migration bất đồng bộ."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Chạy migration ở chế độ online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

