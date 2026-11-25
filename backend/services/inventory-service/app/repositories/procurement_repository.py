"""
Module: app.repositories.procurement_repository (Inventory Service)
Nhiệm vụ: Tầng truy xuất cơ sở dữ liệu (`fruitstore_inventory_db`) cho phân hệ
          Nhà cung cấp (`suppliers`), Phiếu nhập kho (`purchase_orders`,
          `purchase_items`) và ghi lô/sổ cái khi xác nhận nhập kho (FR-C01..C03,
          NFR-P02).
          Tận dụng các index sẵn có (`ix_suppliers_code`,
          `ix_purchase_orders_supplier_id`, `ix_purchase_orders_status`,
          `ix_purchase_orders_po_number`) và dùng `selectinload` tránh N+1 query.
"""

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import (
    PurchaseOrder,
    StockLot,
    StockMovement,
    Supplier,
)


class ProcurementRepository:
    """Repository thao tác SQLAlchemy 2.0 Async cho Nhà cung cấp và Phiếu nhập kho."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _supports_row_lock(self) -> bool:
        """Kiểm tra dialect hiện tại có hỗ trợ `SELECT ... FOR UPDATE` hay không."""
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind is not None else ""
        return "sqlite" not in dialect_name.lower()

    # =========================================================================
    # 1. TRUY VẤN NHÀ CUNG CẤP (SUPPLIERS - FR-C01)
    # =========================================================================
    async def get_supplier_by_id(self, supplier_id: UUID) -> Optional[Supplier]:
        """Tìm một nhà cung cấp theo khóa chính UUID."""
        stmt = select(Supplier).where(Supplier.id == supplier_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_supplier_by_code(self, code: str) -> Optional[Supplier]:
        """Tìm nhà cung cấp theo mã duy nhất `code` (có index `ix_suppliers_code`)."""
        stmt = select(Supplier).where(func.upper(Supplier.code) == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_supplier_codes_by_prefix(self, prefix: str) -> List[str]:
        """Lấy danh sách mã nhà cung cấp bắt đầu bằng tiền tố (ví dụ `NCC-`)."""
        stmt = select(Supplier.code).where(Supplier.code.like(f"{prefix}%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_suppliers(
        self,
        q: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Supplier], int]:
        """
        Truy vấn danh sách nhà cung cấp có lọc theo từ khóa (tên, SĐT, mã),
        trạng thái `is_active` và phân trang.
        """
        filters = []
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Supplier.name.ilike(pattern),
                    Supplier.phone.ilike(pattern),
                    Supplier.code.ilike(pattern),
                )
            )
        if is_active is not None:
            filters.append(Supplier.is_active == is_active)

        count_stmt = select(func.count(Supplier.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = max(0, (page - 1) * limit)
        stmt = (
            select(Supplier)
            .order_by(Supplier.created_at.desc(), Supplier.code.asc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    def add_supplier(self, supplier: Supplier) -> None:
        """Thêm đối tượng `Supplier` mới vào session hiện tại."""
        self.session.add(supplier)

    # =========================================================================
    # 2. TRUY VẤN PHIẾU NHẬP KHO (PURCHASE ORDERS - FR-C02, NFR-P02)
    # =========================================================================
    async def get_purchase_order_by_id(
        self, po_id: UUID, for_update: bool = False
    ) -> Optional[PurchaseOrder]:
        """
        Lấy chi tiết phiếu nhập kho kèm thông tin NCC và danh sách dòng sản phẩm.
        Hỗ trợ khóa dòng `FOR UPDATE` khi chốt nhập kho hoặc hủy phiếu.
        """
        stmt = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items),
            )
            .where(PurchaseOrder.id == po_id)
        )
        if for_update and self._supports_row_lock():
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_po_numbers_by_prefix(self, prefix: str) -> List[str]:
        """Lấy danh sách `po_number` theo tiền tố tháng `PO-YYYYMM-` để sinh số tuần tự."""
        stmt = select(PurchaseOrder.po_number).where(
            PurchaseOrder.po_number.like(f"{prefix}%")
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_purchase_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[PurchaseOrder], int]:
        """
        Lấy danh sách phiếu nhập kho có lọc theo trạng thái (`status`),
        nhà cung cấp (`supplier_id`), khoảng ngày (`from_date`..`to_date`)
        và phân trang. Tận dụng index `supplier_id`, `status` (NFR-P02).
        """
        filters = []
        if status:
            filters.append(PurchaseOrder.status == status.upper())
        if supplier_id:
            filters.append(PurchaseOrder.supplier_id == supplier_id)
        if from_date:
            filters.append(
                PurchaseOrder.created_at
                >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
            )
        if to_date:
            filters.append(
                PurchaseOrder.created_at
                <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)
            )

        count_stmt = select(func.count(PurchaseOrder.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = max(0, (page - 1) * limit)
        stmt = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items),
            )
            .order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.po_number.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    def add_purchase_order(self, purchase_order: PurchaseOrder) -> None:
        """Thêm đối tượng `PurchaseOrder` (cùng các `PurchaseItem`) vào session."""
        self.session.add(purchase_order)

    # =========================================================================
    # 3. TRUY VẤN & GHI LÔ HÀNG / SỔ CÁI KHI NHẬN HÀNG (FR-C03, BR-03)
    # =========================================================================
    async def lot_code_exists(self, lot_code: str) -> bool:
        """Kiểm tra `lot_code` đã tồn tại trong bảng `stock_lots` hay chưa."""
        stmt = select(StockLot.id).where(StockLot.lot_code == lot_code).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def add_stock_lot(self, lot: StockLot) -> None:
        """Thêm bản ghi `StockLot` mới vào session trong cùng transaction."""
        self.session.add(lot)

    def add_stock_movement(self, movement: StockMovement) -> None:
        """Thêm bản ghi sổ cái bất biến `StockMovement` vào session."""
        self.session.add(movement)
