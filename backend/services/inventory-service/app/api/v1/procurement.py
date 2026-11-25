"""
Module: app.api.v1.procurement (Inventory Service)
Nhiệm vụ: Mở các REST API endpoints cho phân hệ Nhà cung cấp (`suppliers`) và
          Phiếu nhập kho (`purchase_orders`) của Thành viên 2 (tiền tố `/api/v1/inventory`):
          - Nhà cung cấp (FR-C01): `GET /suppliers`, `GET /suppliers/{id}`,
            `POST /suppliers`, `PATCH /suppliers/{id}`.
          - Phiếu nhập kho (FR-C02): `GET /purchase-orders`, `GET /purchase-orders/{id}`,
            `POST /purchase-orders`, `POST /purchase-orders/{id}/cancel`.
          - Xác nhận nhập kho sinh lô FEFO (FR-C03, BR-03, AC-01):
            `POST /purchase-orders/{id}/receive`.
          - Phân quyền RBAC (NFR-S03): Bắt buộc `X-Internal-Key` và vai trò
            `WAREHOUSE`, `MANAGER` hoặc `ADMIN` (`STAFF`, `CUSTOMER` bị trả `403`).
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor, require_roles, verify_internal_key
from app.db.session import get_db
from app.schemas.procurement import (
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
from app.services.procurement_service import ProcurementService

# Phân quyền chuẩn theo SRS (Mục 2.8 / NFR-S03):
# WAREHOUSE, MANAGER, ADMIN được phép; STAFF và CUSTOMER nhận 403 FORBIDDEN.
require_procurement_access = require_roles("WAREHOUSE", "MANAGER", "ADMIN")

router = APIRouter(
    prefix="/inventory",
    dependencies=[Depends(verify_internal_key)],
)


def _extract_request_id(request: Request) -> Optional[str]:
    """Lấy `X-Request-ID` từ request hiện tại để truyền tiếp khi gọi Catalog Service."""
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id")


# =============================================================================
# 1. ENDPOINTS NHÀ CUNG CẤP (SUPPLIERS - FR-C01)
# =============================================================================
@router.get(
    "/suppliers",
    response_model=SupplierListResponse,
    tags=["Suppliers"],
    summary="Danh sách nhà cung cấp (tìm theo tên/SĐT, lọc is_active, phân trang)",
)
async def list_suppliers(
    q: Optional[str] = Query(
        default=None, description="Từ khóa tìm theo tên, số điện thoại hoặc mã NCC"
    ),
    is_active: Optional[bool] = Query(
        default=None, description="Lọc theo trạng thái đang hoạt động"
    ),
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    limit: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> SupplierListResponse:
    """Lấy danh sách nhà cung cấp có hỗ trợ tìm kiếm, lọc và phân trang."""
    service = ProcurementService(session)
    return await service.list_suppliers(q=q, is_active=is_active, page=page, limit=limit)


@router.get(
    "/suppliers/{supplier_id}",
    response_model=SupplierResponse,
    tags=["Suppliers"],
    summary="Xem chi tiết nhà cung cấp",
)
async def get_supplier(
    supplier_id: UUID,
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Trả về thông tin chi tiết của một nhà cung cấp theo UUID."""
    service = ProcurementService(session)
    return await service.get_supplier(supplier_id=supplier_id)


@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Suppliers"],
    summary="Tạo nhà cung cấp mới với mã duy nhất dạng NCC-001",
)
async def create_supplier(
    payload: SupplierCreate,
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Tạo mới nhà cung cấp; trả `409 SUPPLIER_CODE_EXISTS` nếu trùng mã."""
    service = ProcurementService(session)
    return await service.create_supplier(payload=payload)


@router.patch(
    "/suppliers/{supplier_id}",
    response_model=SupplierResponse,
    tags=["Suppliers"],
    summary="Cập nhật thông tin hoặc trạng thái hoạt động của nhà cung cấp",
)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Cập nhật nhà cung cấp theo UUID."""
    service = ProcurementService(session)
    return await service.update_supplier(supplier_id=supplier_id, payload=payload)


# =============================================================================
# 2. ENDPOINTS PHIẾU NHẬP KHO (PURCHASE ORDERS - FR-C02, FR-C03)
# =============================================================================
@router.get(
    "/purchase-orders",
    response_model=PurchaseOrderListResponse,
    tags=["Purchase Orders"],
    summary="Danh sách phiếu nhập kho (lọc theo trạng thái, NCC, khoảng ngày, phân trang)",
)
async def list_purchase_orders(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Lọc theo trạng thái phiếu: DRAFT, RECEIVED, CANCELLED",
    ),
    supplier_id: Optional[UUID] = Query(
        default=None, description="Lọc theo UUID nhà cung cấp"
    ),
    from_date: Optional[date] = Query(
        default=None, description="Lọc phiếu tạo từ ngày (YYYY-MM-DD)"
    ),
    to_date: Optional[date] = Query(
        default=None, description="Lọc phiếu tạo đến ngày (YYYY-MM-DD)"
    ),
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    limit: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderListResponse:
    """Tra cứu danh sách phiếu nhập kho có bộ lọc và phân trang."""
    service = ProcurementService(session)
    return await service.list_purchase_orders(
        status=status_filter,
        supplier_id=supplier_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )


@router.get(
    "/purchase-orders/{po_id}",
    response_model=PurchaseOrderResponse,
    tags=["Purchase Orders"],
    summary="Xem chi tiết phiếu nhập kho kèm danh sách dòng sản phẩm",
)
async def get_purchase_order(
    po_id: UUID,
    _: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderResponse:
    """Lấy thông tin chi tiết một phiếu nhập kho và các dòng hàng."""
    service = ProcurementService(session)
    return await service.get_purchase_order(po_id=po_id)


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Purchase Orders"],
    summary="Lập phiếu nhập kho mới (DRAFT, tự sinh PO-YYYYMM-NNN và tính tổng tiền)",
)
async def create_purchase_order(
    request: Request,
    payload: PurchaseOrderCreate,
    actor: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderResponse:
    """Lập phiếu nhập nháp và xác thực `product_id` qua Catalog Service (SOA)."""
    service = ProcurementService(session)
    return await service.create_purchase_order(
        payload=payload,
        actor=actor,
        request_id=_extract_request_id(request),
    )


@router.post(
    "/purchase-orders/{po_id}/receive",
    response_model=PurchaseOrderReceiveResponse,
    tags=["Purchase Orders"],
    summary="Xác nhận nhập kho nguyên tử -> RECEIVED, sinh stock_lots và stock_movements (IN)",
)
async def receive_purchase_order(
    po_id: UUID,
    request: Request,
    payload: Optional[PurchaseOrderReceiveRequest] = Body(default=None),
    actor: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderReceiveResponse:
    """Chốt phiếu nhập kho trong 1 transaction nguyên tử, sinh lô FEFO và ghi sổ cái `IN`."""
    service = ProcurementService(session)
    return await service.receive_purchase_order(
        po_id=po_id,
        actor=actor,
        payload=payload,
        request_id=_extract_request_id(request),
    )


@router.post(
    "/purchase-orders/{po_id}/cancel",
    response_model=PurchaseOrderResponse,
    tags=["Purchase Orders"],
    summary="Hủy phiếu nhập kho ở trạng thái DRAFT",
)
async def cancel_purchase_order(
    po_id: UUID,
    actor: Actor = Depends(require_procurement_access),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderResponse:
    """Chuyển trạng thái phiếu nhập nháp (`DRAFT`) sang `CANCELLED`."""
    service = ProcurementService(session)
    return await service.cancel_purchase_order(po_id=po_id, actor=actor)
