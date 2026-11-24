"""
Module: app.models.inventory (Inventory Service)
Nhiệm vụ: Định nghĩa 7 ORM models SQLAlchemy 2.0 Async cho `fruitstore_inventory_db`:
          1. `Supplier` (`suppliers`): Danh mục nhà cung cấp trái cây (FR-C01).
          2. `PurchaseOrder` (`purchase_orders`): Phiếu nhập kho (FR-C02).
          3. `PurchaseItem` (`purchase_items`): Chi tiết dòng sản phẩm trên phiếu nhập (FR-C02).
          4. `StockLot` (`stock_lots`): Lô hàng tồn kho quản lý theo hạn sử dụng FEFO (FR-C03..C06, BR-01..04).
          5. `Reservation` (`reservations`): Phiếu giữ tạm tồn kho TTL 15 phút (FR-C10..C13, BR-06, BR-08).
          6. `ReservationItem` (`reservation_items`): Chi tiết phân bổ giữ tạm theo từng lô FEFO.
          7. `StockMovement` (`stock_movements`): Sổ cái biến động kho bất biến (BR-05, FR-C07..C09).
          Tuân thủ NFR-K04: Khóa chính `UUID`, tiền tệ `NUMERIC(14,2)`, khối lượng `NUMERIC(10,3)`.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Supplier(Base):
    """Bảng `suppliers`: Danh mục nhà cung cấp trái cây."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        back_populates="supplier"
    )
    stock_lots: Mapped[List["StockLot"]] = relationship(back_populates="supplier")


class PurchaseOrder(Base):
    """Bảng `purchase_orders`: Phiếu nhập hàng từ nhà cung cấp (DRAFT | RECEIVED | CANCELLED)."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_po_total_amount_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    po_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", server_default="DRAFT", index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[List["PurchaseItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    stock_lots: Mapped[List["StockLot"]] = relationship(back_populates="purchase_order")


class PurchaseItem(Base):
    """Bảng `purchase_items`: Chi tiết từng dòng sản phẩm trái cây trong phiếu nhập kho."""

    __tablename__ = "purchase_items"
    __table_args__ = (
        CheckConstraint("quantity_ordered > 0", name="chk_po_item_qty_ordered_pos"),
        CheckConstraint("quantity_received >= 0", name="chk_po_item_qty_received_nonneg"),
        CheckConstraint("unit_cost >= 0", name="chk_po_item_unit_cost_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default=text("0"),
    )
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expected_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")


class StockLot(Base):
    """Bảng `stock_lots`: Lô hàng tồn kho theo hạn sử dụng (FEFO) và ràng buộc không tồn âm (BR-02)."""

    __tablename__ = "stock_lots"
    __table_args__ = (
        CheckConstraint("quantity_received > 0", name="chk_lot_qty_received_pos"),
        CheckConstraint("quantity_remaining >= 0", name="chk_lot_qty_remaining_nonneg"),
        CheckConstraint("quantity_reserved >= 0", name="chk_lot_qty_reserved_nonneg"),
        CheckConstraint(
            "quantity_remaining >= quantity_reserved", name="chk_lot_available"
        ),
        CheckConstraint("unit_cost >= 0", name="chk_lot_unit_cost_nonneg"),
        CheckConstraint(
            "expiry_date >= received_date", name="chk_lot_expiry_after_received"
        ),
        Index(
            "idx_stock_lots_fefo",
            "product_id",
            "expiry_date",
            postgresql_where=text(
                "status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > quantity_reserved"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lot_code: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    quantity_remaining: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default=text("0"),
    )
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="stock_lots")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship(
        back_populates="stock_lots"
    )
    movements: Mapped[List["StockMovement"]] = relationship(back_populates="lot")
    reservation_items: Mapped[List["ReservationItem"]] = relationship(
        back_populates="lot"
    )


class Reservation(Base):
    """Bảng `reservations`: Phiếu giữ hàng tạm thời theo FEFO có TTL 15 phút (BR-06, BR-08)."""

    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    items: Mapped[List["ReservationItem"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationItem(Base):
    """Bảng `reservation_items`: Chi tiết phân bổ giữ tạm theo từng lô FEFO."""

    __tablename__ = "reservation_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_reservation_item_qty_pos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stock_lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    reservation: Mapped["Reservation"] = relationship(back_populates="items")
    lot: Mapped["StockLot"] = relationship(back_populates="reservation_items")


class StockMovement(Base):
    """Bảng `stock_movements`: Sổ cái biến động kho bất biến (IN | SALE_OUT | WASTE_EXPIRED | WASTE_DAMAGED | ADJUSTMENT)."""

    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stock_lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(
        String(25), nullable=False, index=True
    )
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_cost_snapshot: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    lot: Mapped["StockLot"] = relationship(back_populates="movements")
