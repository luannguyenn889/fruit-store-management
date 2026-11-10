"""
Module: app.models.catalog
Nhiệm vụ: Định nghĩa các bảng ORM của `fruitstore_catalog_db` theo đặc tả SRS v1.3:
          - `categories`: Danh mục trái cây (khóa chính UUID, slug duy nhất).
          - `products`: Sản phẩm trái cây (SKU duy nhất, đơn vị `kg|hop|qua`, đơn giá `Numeric(14,2)`,
            xuất xứ, hạn sử dụng gợi ý `default_shelf_life_days`, điều kiện bảo quản, trạng thái).
          - `product_images`: Hình ảnh sản phẩm (lưu đường dẫn ảnh, không lưu BYTEA - NFR-K04).
          - `price_history`: Lịch sử thay đổi đơn giá bất biến (FR-B06, BR-07).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Trả về thời gian UTC hiện tại có nhận biết múi giờ (timezone-aware)."""
    return datetime.now(timezone.utc)


class Category(Base):
    """Model bảng `categories` quản lý danh mục phân loại trái cây (FR-B03)."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="category", lazy="selectin"
    )


class Product(Base):
    """
    Model bảng `products` lưu trữ thông tin sản phẩm trái cây (FR-B01..B05, FR-B08).
    Tuân thủ NFR-K04: Tiền tệ dùng `Numeric(14, 2)`, khóa chính `UUID`.
    """

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit IN ('kg', 'hop', 'qua')", name="ck_products_unit"),
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        CheckConstraint(
            "default_shelf_life_days > 0",
            name="ck_products_shelf_life_pos",
        ),
        CheckConstraint(
            "storage_condition IN ('AMBIENT', 'COOL_2_8C', 'COOL_8_12C')",
            name="ck_products_storage_condition",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'OUT_OF_SEASON')",
            name="ck_products_status",
        ),
        Index("idx_products_category_status", "category_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(220), unique=True, nullable=False, index=True
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="kg"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    origin: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    default_shelf_life_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    storage_condition: Mapped[str] = mapped_column(
        String(30), nullable=False, default="COOL_2_8C"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    category: Mapped[Category] = relationship(
        "Category", back_populates="products", lazy="selectin"
    )
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    price_histories: Mapped[List["PriceHistory"]] = relationship(
        "PriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(PriceHistory.effective_at)",
        lazy="selectin",
    )


class ProductImage(Base):
    """Model bảng `product_images` lưu trữ đường dẫn hình ảnh sản phẩm (FR-B07)."""

    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    product: Mapped[Product] = relationship("Product", back_populates="images")


class PriceHistory(Base):
    """
    Model bảng `price_history` lưu vết mọi lần thay đổi đơn giá bán (FR-B06, BR-07).
    Bất biến: Không được phép cập nhật hoặc xóa bản ghi lịch sử giá.
    `changed_by_user_id` là tham chiếu logic tới `users.id` bên Auth Service (không FK xuyên DB).
    """

    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint("old_price >= 0", name="ck_price_history_old_nonneg"),
        CheckConstraint("new_price >= 0", name="ck_price_history_new_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    new_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    product: Mapped[Product] = relationship(
        "Product", back_populates="price_histories"
    )

