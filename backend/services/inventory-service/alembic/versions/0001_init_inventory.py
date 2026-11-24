"""Khởi tạo 7 bảng cho fruitstore_inventory_db và index tối ưu FEFO.

Revision ID: 0001_init_inventory
Revises:
Create Date: 2026-11-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_init_inventory"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tạo 7 bảng nghiệp vụ kho FEFO, các CHECK constraints và partial index FEFO."""
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("po_number", sa.String(length=50), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(precision=14, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("total_amount >= 0", name="chk_po_total_amount_nonneg"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"], unique=True)
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"], unique=False)
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"], unique=False)

    op.create_table(
        "purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_ordered", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column(
            "quantity_received",
            sa.Numeric(precision=10, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("unit_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("expected_expiry_date", sa.Date(), nullable=True),
        sa.CheckConstraint("quantity_ordered > 0", name="chk_po_item_qty_ordered_pos"),
        sa.CheckConstraint("quantity_received >= 0", name="chk_po_item_qty_received_nonneg"),
        sa.CheckConstraint("unit_cost >= 0", name="chk_po_item_unit_cost_nonneg"),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_items_purchase_order_id", "purchase_items", ["purchase_order_id"], unique=False)
    op.create_index("ix_purchase_items_product_id", "purchase_items", ["product_id"], unique=False)

    op.create_table(
        "stock_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_code", sa.String(length=60), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity_received", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column(
            "quantity_reserved",
            sa.Numeric(precision=10, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("unit_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'AVAILABLE'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity_received > 0", name="chk_lot_qty_received_pos"),
        sa.CheckConstraint("quantity_remaining >= 0", name="chk_lot_qty_remaining_nonneg"),
        sa.CheckConstraint("quantity_reserved >= 0", name="chk_lot_qty_reserved_nonneg"),
        sa.CheckConstraint(
            "quantity_remaining >= quantity_reserved", name="chk_lot_available"
        ),
        sa.CheckConstraint("unit_cost >= 0", name="chk_lot_unit_cost_nonneg"),
        sa.CheckConstraint(
            "expiry_date >= received_date", name="chk_lot_expiry_after_received"
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"], ["purchase_orders.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_lots_lot_code", "stock_lots", ["lot_code"], unique=True)
    op.create_index("ix_stock_lots_product_id", "stock_lots", ["product_id"], unique=False)
    op.create_index("ix_stock_lots_supplier_id", "stock_lots", ["supplier_id"], unique=False)
    op.create_index("ix_stock_lots_purchase_order_id", "stock_lots", ["purchase_order_id"], unique=False)
    op.create_index("ix_stock_lots_expiry_date", "stock_lots", ["expiry_date"], unique=False)
    op.create_index("ix_stock_lots_status", "stock_lots", ["status"], unique=False)
    op.create_index(
        "idx_stock_lots_fefo",
        "stock_lots",
        ["product_id", "expiry_date"],
        unique=False,
        postgresql_where=sa.text(
            "status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > quantity_reserved"
        ),
    )

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_order_id", "reservations", ["order_id"], unique=True)
    op.create_index("ix_reservations_idempotency_key", "reservations", ["idempotency_key"], unique=True)
    op.create_index("ix_reservations_status", "reservations", ["status"], unique=False)
    op.create_index("ix_reservations_expires_at", "reservations", ["expires_at"], unique=False)

    op.create_table(
        "reservation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.CheckConstraint("quantity > 0", name="chk_reservation_item_qty_pos"),
        sa.ForeignKeyConstraint(["lot_id"], ["stock_lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservation_items_reservation_id", "reservation_items", ["reservation_id"], unique=False)
    op.create_index("ix_reservation_items_lot_id", "reservation_items", ["lot_id"], unique=False)
    op.create_index("ix_reservation_items_product_id", "reservation_items", ["product_id"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(length=25), nullable=False),
        sa.Column("quantity_change", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["stock_lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_stock_movements_idempotency_key"),
    )
    op.create_index("ix_stock_movements_lot_id", "stock_movements", ["lot_id"], unique=False)
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"], unique=False)
    op.create_index("ix_stock_movements_reference_id", "stock_movements", ["reference_id"], unique=False)
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"], unique=False)


def downgrade() -> None:
    """Xóa toàn bộ 7 bảng Inventory Service theo đúng thứ tự phụ thuộc khóa ngoại."""
    op.drop_table("stock_movements")
    op.drop_table("reservation_items")
    op.drop_table("reservations")
    op.drop_index("idx_stock_lots_fefo", table_name="stock_lots")
    op.drop_table("stock_lots")
    op.drop_table("purchase_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
