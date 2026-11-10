"""
Module: app.db.base (Catalog Service)
Nhiệm vụ: Khai báo lớp cơ sở `Base` (DeclarativeBase của SQLAlchemy 2.0) cho toàn bộ
          các bảng dữ liệu thuộc `fruitstore_catalog_db`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở ORM cho các model trong Catalog Service."""

    pass

