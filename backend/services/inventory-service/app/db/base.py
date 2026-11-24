"""
Module: app.db.base (Inventory Service)
Nhiệm vụ: Khai báo lớp cơ sở `Base` (DeclarativeBase của SQLAlchemy 2.0) cho toàn bộ
          7 bảng dữ liệu thuộc `fruitstore_inventory_db`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở ORM cho các model trong Inventory Service."""

    pass
