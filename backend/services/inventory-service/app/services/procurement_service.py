"""
Module: app.services.procurement_service (Inventory Service)
Nhiệm vụ: Tầng xử lý nghiệp vụ cho Nhà cung cấp và Phiếu nhập kho (Thành viên 2):
          - CRUD Nhà cung cấp (`suppliers`) với mã duy nhất `NCC-xxx` (FR-C01).
          - Lập phiếu nhập kho (`DRAFT`), sinh số phiếu `PO-YYYYMM-NNN`, tự tính
            `total_amount` bằng `Decimal` (FR-C02, NFR-K04).
          - Kiểm tra hợp lệ `product_id` qua REST tới `catalog-service` theo kiến
            trúc SOA, tuyệt đối không JOIN chéo database.
          - Xác nhận nhập kho nguyên tử (`POST /purchase-orders/{id}/receive`):
            chốt `RECEIVED`, tự sinh `stock_lots` (`quantity_remaining = quantity_received`,
            `quantity_reserved = 0`) và ghi sổ cái `stock_movements` loại `IN`
            trong 1 transaction duy nhất (FR-C03, BR-03, BR-05, AC-01).
          - Hủy phiếu nhập nháp (`DRAFT` -> `CANCELLED`, FR-C02).
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
import re
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import Actor
from app.core.exceptions import AppError
from app.models.inventory import (
    PurchaseItem,
    PurchaseOrder,
    StockLot,
    StockMovement,
    Supplier,
)
from app.repositories.procurement_repository import ProcurementRepository
from app.schemas.procurement import (
    CreatedStockLotSummary,
    CreatedStockMovementSummary,
    PurchaseItemReceiveInput,
    PurchaseItemResponse,
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderReceiveRequest,
    PurchaseOrderReceiveResponse,
    PurchaseOrderResponse,
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)

VALID_PO_STATUSES = {"DRAFT", "RECEIVED", "CANCELLED"}
TWO_PLACES = Decimal("0.01")
ZERO_QTY = Decimal("0.000")
SUPPLIER_SEQ_RE = re.compile(r"^NCC-(\d+)$")
PO_SEQ_RE = re.compile(r"^PO-\d{6}-(\d+)$")


class ProcurementService:
    """Dịch vụ nghiệp vụ quản lý nhà cung cấp, phiếu nhập kho và chốt nhập sinh lô."""

    def __init__(
        self,
        session: AsyncSession,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.session = session
        self.repo = ProcurementRepository(session)
        self._http_client = http_client

    # =========================================================================
    # HÀM HỖ TRỢ NỘI BỘ (MAPPING, TÍNH TOÁN DECIMAL & XÁC THỰC CATALOG SOA)
    # =========================================================================
    @staticmethod
    def _quantize_money(amount: Decimal) -> Decimal:
        """Làm tròn số tiền VNĐ chính xác 2 chữ số thập phân (NUMERIC(14,2))."""
        return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @classmethod
    def _to_purchase_item_response(cls, item: PurchaseItem) -> PurchaseItemResponse:
        """Chuyển đổi ORM `PurchaseItem` sang DTO kèm thành tiền từng dòng."""
        qty_for_total = (
            item.quantity_received
            if item.quantity_received > ZERO_QTY
            else item.quantity_ordered
        )
        line_total = cls._quantize_money(qty_for_total * item.unit_cost)
        return PurchaseItemResponse(
            id=item.id,
            purchase_order_id=item.purchase_order_id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            quantity_received=item.quantity_received,
            unit_cost=item.unit_cost,
            line_total=line_total,
            expected_expiry_date=item.expected_expiry_date,
        )

    @classmethod
    def _to_purchase_order_response(cls, po: PurchaseOrder) -> PurchaseOrderResponse:
        """Chuyển đổi ORM `PurchaseOrder` (đã nạp `supplier` và `items`) sang DTO."""
        supplier = po.supplier
        return PurchaseOrderResponse(
            id=po.id,
            po_number=po.po_number,
            supplier_id=po.supplier_id,
            supplier_code=supplier.code if supplier else None,
            supplier_name=supplier.name if supplier else None,
            status=po.status,
            total_amount=po.total_amount,
            created_by_user_id=po.created_by_user_id,
            received_at=po.received_at,
            created_at=po.created_at,
            items=[cls._to_purchase_item_response(i) for i in po.items],
        )

    @staticmethod
    def _determine_initial_lot_status(received_date: date, expiry_date: date) -> str:
        """Xác định trạng thái ban đầu của lô vừa nhập theo ngưỡng cận hạn SRS."""
        near_threshold = received_date + timedelta(days=settings.NEAR_EXPIRY_DAYS)
        if expiry_date <= near_threshold:
            return "NEAR_EXPIRY"
        return "AVAILABLE"

    async def _generate_next_supplier_code(self) -> str:
        """Tự động sinh mã nhà cung cấp tuần tự dạng `NCC-001`, `NCC-002`, ..."""
        existing_codes = await self.repo.list_supplier_codes_by_prefix("NCC-")
        max_seq = 0
        for code in existing_codes:
            match = SUPPLIER_SEQ_RE.match(code.upper())
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return f"NCC-{max_seq + 1:03d}"

    async def _generate_next_po_number(self, now: datetime) -> str:
        """Sinh mã phiếu nhập kho tuần tự theo tháng dạng `PO-YYYYMM-NNN` (FR-C02)."""
        prefix = f"PO-{now.strftime('%Y%m')}-"
        existing_numbers = await self.repo.list_po_numbers_by_prefix(prefix)
        max_seq = 0
        for number in existing_numbers:
            match = PO_SEQ_RE.match(number.upper())
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return f"{prefix}{max_seq + 1:03d}"

    async def _fetch_catalog_product(
        self,
        client: httpx.AsyncClient,
        product_id: UUID,
        headers: Dict[str, str],
    ) -> Tuple[UUID, int]:
        """Gọi REST `GET /api/v1/catalog/products/{id}` để kiểm tra sản phẩm tồn tại."""
        url = (
            f"{settings.CATALOG_SERVICE_URL.rstrip('/')}"
            f"{settings.API_V1_STR}/catalog/products/{product_id}"
        )
        try:
            response = await client.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise AppError(
                status_code=502,
                code="CATALOG_SERVICE_UNAVAILABLE",
                message="Không thể kết nối tới Catalog Service để xác thực sản phẩm.",
                details={"product_id": str(product_id), "reason": str(exc)},
            ) from exc
        return product_id, response.status_code

    async def validate_products_in_catalog(
        self,
        product_ids: Iterable[UUID],
        request_id: Optional[str] = None,
    ) -> None:
        """
        Kiểm tra toàn bộ `product_id` có tồn tại bên Catalog Service qua REST API (SOA).
        Chạy đồng thời bằng `asyncio.gather` để tối ưu độ trễ (NFR-P02).
        """
        unique_ids = list(dict.fromkeys(product_ids))
        if not unique_ids:
            return

        headers: Dict[str, str] = {"X-Internal-Key": settings.INTERNAL_API_KEY}
        if request_id:
            headers["X-Request-ID"] = request_id

        if self._http_client is not None:
            results = await asyncio.gather(
                *(
                    self._fetch_catalog_product(self._http_client, pid, headers)
                    for pid in unique_ids
                )
            )
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                results = await asyncio.gather(
                    *(
                        self._fetch_catalog_product(client, pid, headers)
                        for pid in unique_ids
                    )
                )

        for pid, status_code in results:
            if status_code == 200:
                continue
            if status_code == 404:
                raise AppError(
                    status_code=404,
                    code="PRODUCT_NOT_FOUND",
                    message=f"Sản phẩm {pid} không tồn tại trong Catalog Service.",
                    details={"product_id": str(pid)},
                )
            if status_code == 422:
                raise AppError(
                    status_code=422,
                    code="INVALID_PRODUCT_ID",
                    message=f"Mã sản phẩm {pid} không hợp lệ tại Catalog Service.",
                    details={"product_id": str(pid)},
                )
            raise AppError(
                status_code=502,
                code="CATALOG_SERVICE_ERROR",
                message="Catalog Service trả về phản hồi không hợp lệ khi xác thực sản phẩm.",
                details={"product_id": str(pid), "upstream_status": status_code},
            )

    # =========================================================================
    # 1. NGHIỆP VỤ NHÀ CUNG CẤP (SUPPLIERS - FR-C01)
    # =========================================================================
    async def list_suppliers(
        self,
        q: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> SupplierListResponse:
        """Trả về danh sách nhà cung cấp có lọc theo từ khóa, trạng thái và phân trang."""
        suppliers, total = await self.repo.list_suppliers(
            q=q, is_active=is_active, page=page, limit=limit
        )
        pages = ceil(total / limit) if total > 0 and limit > 0 else 0
        return SupplierListResponse(
            items=[SupplierResponse.model_validate(s) for s in suppliers],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_supplier(self, supplier_id: UUID) -> SupplierResponse:
        """Xem thông tin chi tiết một nhà cung cấp theo UUID."""
        supplier = await self.repo.get_supplier_by_id(supplier_id)
        if not supplier:
            raise AppError(
                status_code=404,
                code="SUPPLIER_NOT_FOUND",
                message=f"Không tìm thấy nhà cung cấp {supplier_id}.",
                details={"supplier_id": str(supplier_id)},
            )
        return SupplierResponse.model_validate(supplier)

    async def create_supplier(self, payload: SupplierCreate) -> SupplierResponse:
        """
        Tạo mới nhà cung cấp với mã `code` duy nhất dạng `NCC-001`.
        Trùng mã trả về `409 SUPPLIER_CODE_EXISTS`.
        """
        supplier_code = payload.code or await self._generate_next_supplier_code()
        existing = await self.repo.get_supplier_by_code(supplier_code)
        if existing:
            raise AppError(
                status_code=409,
                code="SUPPLIER_CODE_EXISTS",
                message=f"Mã nhà cung cấp '{supplier_code}' đã tồn tại.",
                details={"code": supplier_code},
            )

        supplier = Supplier(
            code=supplier_code,
            name=payload.name,
            phone=payload.phone,
            address=payload.address,
            is_active=payload.is_active,
        )
        self.repo.add_supplier(supplier)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                status_code=409,
                code="SUPPLIER_CODE_EXISTS",
                message=f"Mã nhà cung cấp '{supplier_code}' đã tồn tại.",
                details={"code": supplier_code},
            ) from exc

        await self.session.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    async def update_supplier(
        self, supplier_id: UUID, payload: SupplierUpdate
    ) -> SupplierResponse:
        """Cập nhật thông tin hoặc bật/tắt trạng thái hoạt động của nhà cung cấp."""
        supplier = await self.repo.get_supplier_by_id(supplier_id)
        if not supplier:
            raise AppError(
                status_code=404,
                code="SUPPLIER_NOT_FOUND",
                message=f"Không tìm thấy nhà cung cấp {supplier_id}.",
                details={"supplier_id": str(supplier_id)},
            )

        updates = payload.model_dump(exclude_unset=True)
        new_code = updates.get("code")
        if new_code and new_code.upper() != supplier.code.upper():
            collision = await self.repo.get_supplier_by_code(new_code)
            if collision and collision.id != supplier.id:
                raise AppError(
                    status_code=409,
                    code="SUPPLIER_CODE_EXISTS",
                    message=f"Mã nhà cung cấp '{new_code}' đã tồn tại.",
                    details={"code": new_code},
                )

        for field_name, field_value in updates.items():
            setattr(supplier, field_name, field_value)
        supplier.updated_at = datetime.now(timezone.utc)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                status_code=409,
                code="SUPPLIER_CODE_EXISTS",
                message="Mã nhà cung cấp bị trùng lặp.",
                details={"code": updates.get("code")},
            ) from exc

        await self.session.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    # =========================================================================
    # 2. NGHIỆP VỤ PHIẾU NHẬP KHO (PURCHASE ORDERS - FR-C02, FR-C03, AC-01)
    # =========================================================================
    async def create_purchase_order(
        self,
        payload: PurchaseOrderCreate,
        actor: Actor,
        request_id: Optional[str] = None,
    ) -> PurchaseOrderResponse:
        """
        Lập phiếu nhập kho mới ở trạng thái `DRAFT`:
        - Kiểm tra nhà cung cấp tồn tại và đang hoạt động.
        - Xác thực toàn bộ `product_id` qua REST gọi Catalog Service (SOA).
        - Tự sinh `po_number` dạng `PO-YYYYMM-NNN` và tính `total_amount` bằng `Decimal`.
        """
        supplier = await self.repo.get_supplier_by_id(payload.supplier_id)
        if not supplier:
            raise AppError(
                status_code=404,
                code="SUPPLIER_NOT_FOUND",
                message=f"Không tìm thấy nhà cung cấp {payload.supplier_id}.",
                details={"supplier_id": str(payload.supplier_id)},
            )
        if not supplier.is_active:
            raise AppError(
                status_code=400,
                code="SUPPLIER_INACTIVE",
                message=f"Nhà cung cấp '{supplier.name}' hiện đang tạm ngừng hoạt động.",
                details={"supplier_id": str(supplier.id)},
            )

        await self.validate_products_in_catalog(
            (item.product_id for item in payload.items),
            request_id=request_id,
        )

        now = datetime.now(timezone.utc)
        po_number = await self._generate_next_po_number(now)
        total_amount = self._quantize_money(
            sum(
                (item.quantity_ordered * item.unit_cost for item in payload.items),
                Decimal("0.00"),
            )
        )

        purchase_order = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier.id,
            status="DRAFT",
            total_amount=total_amount,
            created_by_user_id=actor.id,
        )
        purchase_order.items = [
            PurchaseItem(
                product_id=item.product_id,
                quantity_ordered=item.quantity_ordered,
                quantity_received=ZERO_QTY,
                unit_cost=item.unit_cost,
                expected_expiry_date=item.expected_expiry_date,
            )
            for item in payload.items
        ]

        self.repo.add_purchase_order(purchase_order)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        created = await self.repo.get_purchase_order_by_id(purchase_order.id)
        return self._to_purchase_order_response(created or purchase_order)

    async def list_purchase_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> PurchaseOrderListResponse:
        """Lấy danh sách phiếu nhập kho có lọc theo trạng thái, NCC, khoảng ngày và phân trang."""
        normalized_status: Optional[str] = None
        if status:
            normalized_status = status.strip().upper()
            if normalized_status not in VALID_PO_STATUSES:
                raise AppError(
                    status_code=422,
                    code="INVALID_PURCHASE_ORDER_STATUS",
                    message="Trạng thái lọc phiếu nhập chỉ chấp nhận DRAFT, RECEIVED hoặc CANCELLED.",
                    details={"status": status},
                )

        if from_date and to_date and from_date > to_date:
            raise AppError(
                status_code=422,
                code="INVALID_DATE_RANGE",
                message="Ngày bắt đầu (from_date) không được lớn hơn ngày kết thúc (to_date).",
                details={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                },
            )

        orders, total = await self.repo.list_purchase_orders(
            status=normalized_status,
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
        pages = ceil(total / limit) if total > 0 and limit > 0 else 0
        return PurchaseOrderListResponse(
            items=[self._to_purchase_order_response(po) for po in orders],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_purchase_order(self, po_id: UUID) -> PurchaseOrderResponse:
        """Xem chi tiết một phiếu nhập kho kèm toàn bộ dòng sản phẩm."""
        po = await self.repo.get_purchase_order_by_id(po_id)
        if not po:
            raise AppError(
                status_code=404,
                code="PURCHASE_ORDER_NOT_FOUND",
                message=f"Không tìm thấy phiếu nhập kho {po_id}.",
                details={"purchase_order_id": str(po_id)},
            )
        return self._to_purchase_order_response(po)

    @staticmethod
    def _build_receive_overrides(
        po: PurchaseOrder,
        payload: Optional[PurchaseOrderReceiveRequest],
    ) -> Dict[UUID, PurchaseItemReceiveInput]:
        """Khớp dữ liệu ghi đè thực nhận (nếu có) vào đúng từng dòng `PurchaseItem`."""
        overrides: Dict[UUID, PurchaseItemReceiveInput] = {}
        if not payload or not payload.items:
            return overrides

        items_by_id = {item.id: item for item in po.items}
        items_by_product: Dict[UUID, List[PurchaseItem]] = {}
        for item in po.items:
            items_by_product.setdefault(item.product_id, []).append(item)

        for entry in payload.items:
            target: Optional[PurchaseItem] = None
            if entry.purchase_item_id is not None:
                target = items_by_id.get(entry.purchase_item_id)
            elif entry.product_id is not None:
                candidates = items_by_product.get(entry.product_id, [])
                target = next((c for c in candidates if c.id not in overrides), None)

            if target is None:
                raise AppError(
                    status_code=422,
                    code="INVALID_RECEIVE_ITEM",
                    message="Dòng xác nhận nhập kho không khớp với bất kỳ dòng nào trên phiếu nhập.",
                    details={
                        "purchase_item_id": (
                            str(entry.purchase_item_id) if entry.purchase_item_id else None
                        ),
                        "product_id": str(entry.product_id) if entry.product_id else None,
                    },
                )
            overrides[target.id] = entry
        return overrides

    async def receive_purchase_order(
        self,
        po_id: UUID,
        actor: Actor,
        payload: Optional[PurchaseOrderReceiveRequest] = None,
        request_id: Optional[str] = None,
    ) -> PurchaseOrderReceiveResponse:
        """
        Xác nhận nhập kho nguyên tử trong 1 transaction duy nhất (FR-C03, BR-03, AC-01):
        1. Chặn phiếu đã `RECEIVED` hoặc `CANCELLED`.
        2. Xác thực lại toàn bộ `product_id` qua Catalog Service REST (SOA).
        3. Khóa dòng phiếu nhập (`FOR UPDATE`), đặt `status = RECEIVED`, `received_at = NOW()`.
        4. Với mỗi dòng hàng: sinh `StockLot` (`quantity_remaining = quantity_received`,
           `quantity_reserved = 0`) và ghi `StockMovement` loại `IN`.
        5. Nếu có bất kỳ lỗi nào giữa chừng, rollback toàn bộ transaction.
        """
        preview_po = await self.repo.get_purchase_order_by_id(po_id, for_update=False)
        if not preview_po:
            raise AppError(
                status_code=404,
                code="PURCHASE_ORDER_NOT_FOUND",
                message=f"Không tìm thấy phiếu nhập kho {po_id}.",
                details={"purchase_order_id": str(po_id)},
            )
        if preview_po.status != "DRAFT":
            raise AppError(
                status_code=409,
                code="INVALID_PURCHASE_ORDER_STATUS",
                message=(
                    f"Phiếu nhập {preview_po.po_number} đang ở trạng thái "
                    f"{preview_po.status}, không thể xác nhận nhập kho."
                ),
                details={"status": preview_po.status, "po_number": preview_po.po_number},
            )
        if not preview_po.items:
            raise AppError(
                status_code=400,
                code="EMPTY_PURCHASE_ORDER",
                message="Phiếu nhập không có dòng sản phẩm nào để xác nhận nhập kho.",
            )

        # Kiểm tra Catalog Service trước khi khóa dòng ghi DB
        await self.validate_products_in_catalog(
            (item.product_id for item in preview_po.items),
            request_id=request_id,
        )

        # Khóa dòng phiếu nhập để ngăn chốt trùng đồng thời
        po = await self.repo.get_purchase_order_by_id(po_id, for_update=True)
        if not po:
            raise AppError(
                status_code=404,
                code="PURCHASE_ORDER_NOT_FOUND",
                message=f"Không tìm thấy phiếu nhập kho {po_id}.",
            )
        if po.status != "DRAFT":
            raise AppError(
                status_code=409,
                code="INVALID_PURCHASE_ORDER_STATUS",
                message=(
                    f"Phiếu nhập {po.po_number} đang ở trạng thái "
                    f"{po.status}, không thể xác nhận nhập kho."
                ),
                details={"status": po.status, "po_number": po.po_number},
            )

        overrides = self._build_receive_overrides(po, payload)
        now = datetime.now(timezone.utc)
        received_date = (
            payload.received_date if (payload and payload.received_date) else date.today()
        )

        created_lots: List[StockLot] = []
        created_movements: List[StockMovement] = []
        used_lot_codes: set[str] = set()
        received_total = Decimal("0.00")

        try:
            for idx, item in enumerate(po.items, start=1):
                override = overrides.get(item.id)
                qty_received = (
                    override.quantity_received
                    if (override and override.quantity_received is not None)
                    else item.quantity_ordered
                )
                expiry_date = (
                    override.expiry_date
                    if (override and override.expiry_date is not None)
                    else item.expected_expiry_date
                )

                if qty_received <= ZERO_QTY:
                    raise AppError(
                        status_code=422,
                        code="INVALID_QUANTITY_RECEIVED",
                        message="Số lượng thực nhận phải lớn hơn 0.",
                        details={"purchase_item_id": str(item.id)},
                    )
                if expiry_date is None:
                    raise AppError(
                        status_code=422,
                        code="MISSING_EXPIRY_DATE",
                        message="Mỗi dòng sản phẩm nhập kho bắt buộc có hạn sử dụng (expiry_date).",
                        details={
                            "purchase_item_id": str(item.id),
                            "product_id": str(item.product_id),
                        },
                    )
                if expiry_date < received_date:
                    raise AppError(
                        status_code=422,
                        code="INVALID_EXPIRY_DATE",
                        message="Hạn sử dụng lô hàng (expiry_date) phải lớn hơn hoặc bằng ngày nhập kho.",
                        details={
                            "received_date": received_date.isoformat(),
                            "expiry_date": expiry_date.isoformat(),
                        },
                    )

                if override and override.lot_code:
                    lot_code = override.lot_code
                    if lot_code in used_lot_codes or await self.repo.lot_code_exists(lot_code):
                        raise AppError(
                            status_code=409,
                            code="LOT_CODE_EXISTS",
                            message=f"Mã lô hàng '{lot_code}' đã tồn tại.",
                            details={"lot_code": lot_code},
                        )
                else:
                    lot_code = f"LOT-{po.po_number}-{idx:02d}"
                    if lot_code in used_lot_codes or await self.repo.lot_code_exists(lot_code):
                        lot_code = f"LOT-{po.po_number}-{idx:02d}-{uuid4().hex[:6].upper()}"
                used_lot_codes.add(lot_code)

                lot_status = self._determine_initial_lot_status(received_date, expiry_date)
                item.quantity_received = qty_received
                received_total += qty_received * item.unit_cost

                lot = StockLot(
                    lot_code=lot_code,
                    product_id=item.product_id,
                    supplier_id=po.supplier_id,
                    purchase_order_id=po.id,
                    quantity_received=qty_received,
                    quantity_remaining=qty_received,
                    quantity_reserved=ZERO_QTY,
                    unit_cost=item.unit_cost,
                    received_date=received_date,
                    expiry_date=expiry_date,
                    status=lot_status,
                )
                self.repo.add_stock_lot(lot)
                await self.session.flush()

                movement = StockMovement(
                    lot_id=lot.id,
                    movement_type="IN",
                    quantity_change=qty_received,
                    unit_cost_snapshot=item.unit_cost,
                    reference_type="PURCHASE_ORDER",
                    reference_id=po.id,
                    idempotency_key=f"po-receive:{po.id}:{item.id}",
                    reason=f"Nhập kho theo phiếu {po.po_number}",
                    performed_by_user_id=actor.id,
                )
                self.repo.add_stock_movement(movement)
                created_lots.append(lot)
                created_movements.append(movement)

            po.total_amount = self._quantize_money(received_total)
            po.status = "RECEIVED"
            po.received_at = now

            await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        updated_po = await self.repo.get_purchase_order_by_id(po.id)
        return PurchaseOrderReceiveResponse(
            purchase_order=self._to_purchase_order_response(updated_po or po),
            created_lots=[CreatedStockLotSummary.model_validate(l) for l in created_lots],
            created_movements=[
                CreatedStockMovementSummary.model_validate(m) for m in created_movements
            ],
        )

    async def cancel_purchase_order(
        self, po_id: UUID, actor: Actor  # noqa: ARG002
    ) -> PurchaseOrderResponse:
        """Hủy phiếu nhập kho ở trạng thái nháp (`DRAFT` -> `CANCELLED`, FR-C02)."""
        po = await self.repo.get_purchase_order_by_id(po_id, for_update=True)
        if not po:
            raise AppError(
                status_code=404,
                code="PURCHASE_ORDER_NOT_FOUND",
                message=f"Không tìm thấy phiếu nhập kho {po_id}.",
                details={"purchase_order_id": str(po_id)},
            )
        if po.status != "DRAFT":
            raise AppError(
                status_code=409,
                code="INVALID_PURCHASE_ORDER_STATUS",
                message=(
                    f"Chỉ có thể hủy phiếu nhập ở trạng thái DRAFT "
                    f"(hiện tại: {po.status})."
                ),
                details={"status": po.status, "po_number": po.po_number},
            )

        po.status = "CANCELLED"
        await self.session.commit()

        updated_po = await self.repo.get_purchase_order_by_id(po.id)
        return self._to_purchase_order_response(updated_po or po)
