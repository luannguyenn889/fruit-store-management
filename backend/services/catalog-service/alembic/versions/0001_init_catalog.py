"""
Module: alembic.versions.0001_init_catalog
Nhiệm vụ: Bản migration đầu tiên (`0001_init_catalog`) của `fruitstore_catalog_db`.
          Tạo 4 bảng: `categories`, `products`, `product_images`, `price_history`
          với đầy đủ ràng buộc theo SRS v1.3 (`unit IN ('kg','hop','qua')`, `price >= 0`,
          khóa chính UUID, tiền tệ `Numeric(14, 2)`).
          Hỗ trợ `downgrade()` đầy đủ để rollback độc lập (NFR-M02).

Revision ID: 0001_init_catalog
Revises: None
Create Date: 2026-11-10
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_init_catalog"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nâng cấp schema: Tạo bảng categories, products, product_images, price_history."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    uuid_default = sa.text("gen_random_uuid()") if is_postgres else None

    # 1. Bảng categories (Danh mục trái cây)
    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    # 2. Bảng products (Sản phẩm trái cây)
    op.create_table(
        "products",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column(
            "unit",
            sa.String(length=20),
            server_default="kg",
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("origin", sa.String(length=150), nullable=True),
        sa.Column(
            "default_shelf_life_days",
            sa.Integer(),
            server_default="7",
            nullable=False,
        ),
        sa.Column(
            "storage_condition",
            sa.String(length=30),
            server_default="COOL_2_8C",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "unit IN ('kg', 'hop', 'qua')", name="ck_products_unit"
        ),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        sa.CheckConstraint(
            "default_shelf_life_days > 0", name="ck_products_shelf_life_pos"
        ),
        sa.CheckConstraint(
            "storage_condition IN ('AMBIENT', 'COOL_2_8C', 'COOL_8_12C')",
            name="ck_products_storage_condition",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'OUT_OF_SEASON')",
            name="ck_products_status",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_slug", "products", ["slug"], unique=True)
    op.create_index(
        "idx_products_category_status",
        "products",
        ["category_id", "status"],
        unique=False,
    )

    # 3. Bảng product_images (Hình ảnh sản phẩm)
    op.create_table(
        "product_images",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("product_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("alt_text", sa.String(length=200), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Bảng price_history (Lịch sử thay đổi đơn giá bất biến)
    op.create_table(
        "price_history",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("product_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "old_price", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column(
            "new_price", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("changed_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "effective_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "old_price >= 0", name="ck_price_history_old_nonneg"
        ),
        sa.CheckConstraint(
            "new_price >= 0", name="ck_price_history_new_nonneg"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_history_product_id",
        "price_history",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Hạ cấp schema: Xóa các bảng theo thứ tự ngược lại để rollback độc lập (NFR-M02)."""
    op.drop_index("ix_price_history_product_id", table_name="price_history")
    op.drop_table("price_history")
    op.drop_table("product_images")
    op.drop_index("idx_products_category_status", table_name="products")
    op.drop_index("ix_products_slug", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")

