"""
Module: app.db.base (Chatbot Service)
Nhiệm vụ: Khai báo lớp `Base` SQLAlchemy 2.0 cho tất cả ORM models của Chatbot Service.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở cho toàn bộ bảng trong `fruitstore_chatbot_db`."""
