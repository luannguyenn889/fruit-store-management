"""
Module: tests.test_procurement (Inventory Service)
Nhiệm vụ: Kiểm thử toàn diện phân hệ Nhà cung cấp & Nhập hàng của Thành viên 2
          (FR-C01..C03, BR-03, BR-05, AC-01, NFR-S03, NFR-K04):
          1. CRUD Nhà cung cấp (`GET/POST/PATCH /suppliers`), tìm kiếm theo tên/SĐT,
             lọc `is_active`, phân trang, mã duy nhất `NCC-xxx` (trùng trả `409`).
          2. Lập phiếu nhập kho (`POST /purchase-orders`) nhiều dòng dùng `Decimal`,
             sinh số `PO-YYYYMM-NNN`, tự tính `total_amount`, xác thực `product_id`
             qua REST tới Catalog Service (trả `404` nếu sản phẩm không tồn tại).
          3. AC-01 & Transaction nguyên tử (`POST /purchase-orders/{id}/receive`):
             nhập 50 kg Xoài sinh đúng 1 `StockLot` (`quantity_remaining = 50.000`,
             `quantity_reserved = 0.000`) và 1 `StockMovement` loại `IN`; chặn chốt
             lại phiếu `RECEIVED`/`CANCELLED`; rollback toàn bộ nếu lỗi giữa chừng.
          4. Hủy phiếu nhập nháp (`POST /purchase-orders/{id}/cancel`): chỉ hủy được `DRAFT`.
          5. Ma trận phân quyền RBAC (Mục 2.8 / NFR-S03): `WAREHOUSE`, `MANAGER`,
             `ADMIN` được phép; `STAFF`, `CUSTOMER` nhận `403 FORBIDDEN`.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import re
from typing import Any, Dict, List, Set, Tuple
from uuid import UUID, uuid4

from fastapi import FastAPI
import httpx
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.v1.procurement import router as procurement_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import get_db
from app.models.inventory import PurchaseOrder, StockLot, StockMovement
from app.schemas.procurement import (
    PurchaseOrderListResponse,
    PurchaseOrderReceiveResponse,
    PurchaseOrderResponse,
    SupplierListResponse,
    SupplierResponse,
)
from app.services.procurement_service import ProcurementService

_WAREHOUSE_ID = str(uuid4())
_SAMPLE_SUPPLIER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_SAMPLE_PO_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_SAMPLE_PRODUCT_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _build_test_app() -> FastAPI:
    """Tạo ứng dụng FastAPI cô lập gắn `procurement_router` mà không cần sửa `app/main.py`."""
    test_app = FastAPI(title="Inventory Procurement Test App")
    register_exception_handlers(test_app)
    test_app.include_router(procurement_router, prefix=settings.API_V1_STR)
    return test_app


def _auth_headers(role: str = "WAREHOUSE", user_id: str = _WAREHOUSE_ID) -> Dict[str, str]:
    """Tạo bộ header chuẩn do API Gateway truyền xuống Inventory Service."""
    return {
        "X-Internal-Key": settings.INTERNAL_API_KEY,
        "X-User-Id": user_id,
        "X-User-Role": role,
        "X-Request-ID": "req-proc-test-001",
    }


@pytest_asyncio.fixture()
async def procurement_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Khởi tạo DB SQLite Async cô lập, ứng dụng FastAPI test và bộ giả lập
    Catalog Service REST (`httpx.MockTransport`) ghi nhận đầy đủ request gọi sang Catalog.
    """
    db_file = tmp_path / "inventory_procurement_test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}", echo=False
    )
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    valid_catalog_products: Set[str] = set()
    catalog_calls: List[Tuple[str, Dict[str, str]]] = []

    def _mock_catalog_handler(request: httpx.Request) -> httpx.Response:
        catalog_calls.append((str(request.url), dict(request.headers)))
        if request.headers.get("x-internal-key") != settings.INTERNAL_API_KEY:
            return httpx.Response(403, json={"code": "FORBIDDEN_DIRECT_ACCESS"})
        product_id_str = request.url.path.rstrip("/").split("/")[-1]
        if product_id_str in valid_catalog_products:
            return httpx.Response(
                200, json={"id": product_id_str, "name": "Xoài Cát Hòa Lộc"}
            )
        return httpx.Response(404, json={"code": "PRODUCT_NOT_FOUND"})

    mock_http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_catalog_handler)
    )
    original_init = ProcurementService.__init__

    def _patched_init(
        self: ProcurementService,
        session: AsyncSession,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        original_init(self, session, http_client=http_client or mock_http_client)

    monkeypatch.setattr(ProcurementService, "__init__", _patched_init)

    test_app = _build_test_app()

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    test_app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://testserver"
    ) as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "valid_products": valid_catalog_products,
            "catalog_calls": catalog_calls,
        }

    test_app.dependency_overrides.clear()
    await mock_http_client.aclose()
    await engine.dispose()


# =============================================================================
# 1. KIỂM THỬ CRUD NHÀ CUNG CẤP (FR-C01, MỤC 2.2)
# =============================================================================
async def test_suppliers_crud_search_filter_and_duplicate_code_409(procurement_env):
    """Kiểm tra tạo, tự sinh mã, chặn trùng mã 409, tìm theo tên/SĐT, lọc is_active và PATCH."""
    client: AsyncClient = procurement_env["client"]
    headers = _auth_headers("WAREHOUSE")

    # Tạo NCC-001
    r1 = await client.post(
        "/api/v1/inventory/suppliers",
        headers=headers,
        json={
            "code": "NCC-001",
            "name": "HTX Trái Cây Tiền Giang",
            "phone": "0901234567",
            "address": "Cái Bè, Tiền Giang",
        },
    )
    assert r1.status_code == 201
    s1 = r1.json()
    assert s1["code"] == "NCC-001"
    assert s1["is_active"] is True

    # Trùng mã NCC-001 -> 409 SUPPLIER_CODE_EXISTS
    dup = await client.post(
        "/api/v1/inventory/suppliers",
        headers=headers,
        json={"code": "ncc-001", "name": "NCC Trùng Mã"},
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "SUPPLIER_CODE_EXISTS"

    # Tạo NCC thứ 2 không truyền code -> tự sinh NCC-002
    r2 = await client.post(
        "/api/v1/inventory/suppliers",
        headers=headers,
        json={
            "name": "Nông Sản Đà Lạt",
            "phone": "0988777666",
            "is_active": False,
        },
    )
    assert r2.status_code == 201
    s2 = r2.json()
    assert s2["code"] == "NCC-002"
    assert s2["is_active"] is False

    # Tìm theo SĐT
    search_phone = await client.get(
        "/api/v1/inventory/suppliers",
        headers=headers,
        params={"q": "0988777"},
    )
    assert search_phone.status_code == 200
    assert search_phone.json()["total"] == 1
    assert search_phone.json()["items"][0]["code"] == "NCC-002"

    # Lọc is_active=true và phân trang
    active_list = await client.get(
        "/api/v1/inventory/suppliers",
        headers=headers,
        params={"is_active": "true", "page": 1, "limit": 10},
    )
    assert active_list.status_code == 200
    assert active_list.json()["total"] == 1
    assert active_list.json()["items"][0]["code"] == "NCC-001"

    # PATCH bật hoạt động và cập nhật tên NCC-002
    patched = await client.patch(
        f"/api/v1/inventory/suppliers/{s2['id']}",
        headers=headers,
        json={"name": "Nông Sản Đà Lạt Mới", "is_active": True},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Nông Sản Đà Lạt Mới"
    assert patched.json()["is_active"] is True


# =============================================================================
# 2. KIỂM THỬ LẬP PHIẾU NHẬP, CATALOG SOA & AC-01 NHẬP KHO NGUYÊN TỬ
# =============================================================================
async def test_purchase_order_catalog_validation_and_ac01_receive(procurement_env):
    """
    Kiểm tra luồng đầy đủ FR-C02, FR-C03, SOA Catalog REST và AC-01:
    - Gọi Catalog Service kiểm tra product_id (sản phẩm không có trả 404).
    - Tạo phiếu DRAFT, tự sinh PO-YYYYMM-NNN và tính total_amount bằng Decimal.
    - Xác nhận nhập 50 kg Xoài sinh đúng 1 StockLot và 1 StockMovement loại IN.
    - Chặn xác nhận lại phiếu đã RECEIVED (409).
    """
    client: AsyncClient = procurement_env["client"]
    session_factory = procurement_env["session_factory"]
    valid_products: Set[str] = procurement_env["valid_products"]
    catalog_calls: List[Tuple[str, Dict[str, str]]] = procurement_env["catalog_calls"]
    headers = _auth_headers("WAREHOUSE")

    sup_resp = await client.post(
        "/api/v1/inventory/suppliers",
        headers=headers,
        json={"code": "NCC-001", "name": "Nhà vườn Xoài Cát"},
    )
    supplier_id = sup_resp.json()["id"]

    # Sản phẩm chưa tồn tại trên Catalog -> 404 PRODUCT_NOT_FOUND
    missing_prod = str(uuid4())
    bad_po = await client.post(
        "/api/v1/inventory/purchase-orders",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "items": [
                {
                    "product_id": missing_prod,
                    "quantity_ordered": "10.000",
                    "unit_cost": "30000.00",
                    "expected_expiry_date": (date.today() + timedelta(days=7)).isoformat(),
                }
            ],
        },
    )
    assert bad_po.status_code == 404
    assert bad_po.json()["code"] == "PRODUCT_NOT_FOUND"
    assert any(missing_prod in url for url, _ in catalog_calls)

    # Đăng ký sản phẩm Xoài hợp lệ bên Catalog Service
    mango_id = str(uuid4())
    valid_products.add(mango_id)
    expiry_str = (date.today() + timedelta(days=10)).isoformat()

    # AC-01: Lập phiếu nhập 50.000 kg Xoài @ 32000.00 VNĐ -> total_amount = 1600000.00
    po_resp = await client.post(
        "/api/v1/inventory/purchase-orders",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "items": [
                {
                    "product_id": mango_id,
                    "quantity_ordered": "50.000",
                    "unit_cost": "32000.00",
                    "expected_expiry_date": expiry_str,
                }
            ],
        },
    )
    assert po_resp.status_code == 201
    po_data = po_resp.json()
    assert po_data["status"] == "DRAFT"
    assert re.match(r"^PO-\d{6}-\d{3}$", po_data["po_number"])
    assert Decimal(po_data["total_amount"]) == Decimal("1600000.00")
    assert len(po_data["items"]) == 1

    # Kiểm tra GET danh sách lọc theo status & supplier_id và GET chi tiết
    list_resp = await client.get(
        "/api/v1/inventory/purchase-orders",
        headers=headers,
        params={
            "status": "DRAFT",
            "supplier_id": supplier_id,
            "from_date": date.today().isoformat(),
            "to_date": date.today().isoformat(),
        },
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    detail_resp = await client.get(
        f"/api/v1/inventory/purchase-orders/{po_data['id']}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["po_number"] == po_data["po_number"]

    # Xác nhận nhập kho (AC-01)
    receive_resp = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_data['id']}/receive",
        headers=headers,
    )
    assert receive_resp.status_code == 200
    recv = receive_resp.json()
    assert recv["purchase_order"]["status"] == "RECEIVED"
    assert recv["purchase_order"]["received_at"] is not None
    assert len(recv["created_lots"]) == 1
    assert len(recv["created_movements"]) == 1

    lot_dto = recv["created_lots"][0]
    assert Decimal(lot_dto["quantity_received"]) == Decimal("50.000")
    assert Decimal(lot_dto["quantity_remaining"]) == Decimal("50.000")
    assert Decimal(lot_dto["quantity_reserved"]) == Decimal("0.000")
    assert Decimal(lot_dto["unit_cost"]) == Decimal("32000.00")
    assert lot_dto["status"] == "AVAILABLE"

    mv_dto = recv["created_movements"][0]
    assert mv_dto["movement_type"] == "IN"
    assert Decimal(mv_dto["quantity_change"]) == Decimal("50.000")
    assert mv_dto["reference_type"] == "PURCHASE_ORDER"
    assert mv_dto["reference_id"] == po_data["id"]

    # Đối chiếu trực tiếp trong DB: đúng 1 StockLot và 1 StockMovement loại IN
    async with session_factory() as verify_session:
        lots = list((await verify_session.execute(select(StockLot))).scalars().all())
        movements = list(
            (await verify_session.execute(select(StockMovement))).scalars().all()
        )
        assert len(lots) == 1
        assert len(movements) == 1
        assert movements[0].movement_type == "IN"
        assert movements[0].quantity_change == Decimal("50.000")

    # Chặn xác nhận lại phiếu đã RECEIVED -> 409
    second_receive = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_data['id']}/receive",
        headers=headers,
    )
    assert second_receive.status_code == 409
    assert second_receive.json()["code"] == "INVALID_PURCHASE_ORDER_STATUS"


# =============================================================================
# 3. KIỂM THỬ ROLLBACK NGUYÊN TỬ & HỦY PHIẾU NHÁP (MỤC 2.6, 2.7)
# =============================================================================
async def test_receive_rolls_back_atomically_on_midway_error_and_cancel_draft(
    procurement_env,
):
    """
    Nếu lỗi xảy ra ở dòng thứ 2 trong lúc xác nhận nhập kho, toàn bộ transaction
    (kể cả lô đã flush của dòng 1) phải được rollback sạch sẽ; và kiểm tra hủy DRAFT.
    """
    client: AsyncClient = procurement_env["client"]
    session_factory = procurement_env["session_factory"]
    valid_products: Set[str] = procurement_env["valid_products"]
    headers = _auth_headers("MANAGER")

    sup_resp = await client.post(
        "/api/v1/inventory/suppliers",
        headers=headers,
        json={"code": "NCC-010", "name": "Vựa Trái Cây Miền Tây"},
    )
    supplier_id = sup_resp.json()["id"]

    prod_1 = str(uuid4())
    prod_2 = str(uuid4())
    valid_products.update({prod_1, prod_2})

    # Dòng 1 hợp lệ, dòng 2 có hạn dùng quá khứ -> phải lỗi giữa chừng & rollback dòng 1
    po_resp = await client.post(
        "/api/v1/inventory/purchase-orders",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "items": [
                {
                    "product_id": prod_1,
                    "quantity_ordered": "12.500",
                    "unit_cost": "45000.00",
                    "expected_expiry_date": (date.today() + timedelta(days=5)).isoformat(),
                },
                {
                    "product_id": prod_2,
                    "quantity_ordered": "5.000",
                    "unit_cost": "20000.00",
                    "expected_expiry_date": (date.today() - timedelta(days=1)).isoformat(),
                },
            ],
        },
    )
    assert po_resp.status_code == 201
    po_id = po_resp.json()["id"]

    failed_receive = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_id}/receive",
        headers=headers,
    )
    assert failed_receive.status_code == 422
    assert failed_receive.json()["code"] == "INVALID_EXPIRY_DATE"

    # Đảm bảo rollback hoàn toàn: 0 lô, 0 movement, phiếu vẫn DRAFT
    async with session_factory() as verify_session:
        lots = list((await verify_session.execute(select(StockLot))).scalars().all())
        movements = list(
            (await verify_session.execute(select(StockMovement))).scalars().all()
        )
        po_row = await verify_session.get(PurchaseOrder, UUID(po_id))
        assert len(lots) == 0
        assert len(movements) == 0
        assert po_row is not None
        assert po_row.status == "DRAFT"
        assert po_row.received_at is None

    # Hủy phiếu DRAFT thành công -> CANCELLED
    cancel_resp = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_id}/cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Phiếu đã CANCELLED không thể nhận hàng hay hủy lại -> 409
    receive_cancelled = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_id}/receive",
        headers=headers,
    )
    assert receive_cancelled.status_code == 409

    cancel_again = await client.post(
        f"/api/v1/inventory/purchase-orders/{po_id}/cancel",
        headers=headers,
    )
    assert cancel_again.status_code == 409


# =============================================================================
# 4. KIỂM THỬ MA TRẬN PHÂN QUYỀN RBAC CHO TẤT CẢ ENDPOINT TV2 (MỤC 2.8 / NFR-S03)
# =============================================================================
def _sample_supplier_dto() -> SupplierResponse:
    now = datetime.now(timezone.utc)
    return SupplierResponse(
        id=_SAMPLE_SUPPLIER_ID,
        code="NCC-999",
        name="NCC Mẫu RBAC",
        phone="0909999999",
        address="TP.HCM",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _sample_po_dto() -> PurchaseOrderResponse:
    now = datetime.now(timezone.utc)
    return PurchaseOrderResponse(
        id=_SAMPLE_PO_ID,
        po_number="PO-202611-999",
        supplier_id=_SAMPLE_SUPPLIER_ID,
        supplier_code="NCC-999",
        supplier_name="NCC Mẫu RBAC",
        status="DRAFT",
        total_amount=Decimal("100000.00"),
        created_by_user_id=UUID(_WAREHOUSE_ID),
        received_at=None,
        created_at=now,
        items=[],
    )


RBAC_ENDPOINTS: Tuple[Tuple[str, str, Dict[str, Any] | None, int], ...] = (
    ("GET", "/api/v1/inventory/suppliers", None, 200),
    ("GET", f"/api/v1/inventory/suppliers/{_SAMPLE_SUPPLIER_ID}", None, 200),
    (
        "POST",
        "/api/v1/inventory/suppliers",
        {"code": "NCC-999", "name": "NCC Mẫu RBAC"},
        201,
    ),
    (
        "PATCH",
        f"/api/v1/inventory/suppliers/{_SAMPLE_SUPPLIER_ID}",
        {"name": "NCC Cập Nhật"},
        200,
    ),
    ("GET", "/api/v1/inventory/purchase-orders", None, 200),
    ("GET", f"/api/v1/inventory/purchase-orders/{_SAMPLE_PO_ID}", None, 200),
    (
        "POST",
        "/api/v1/inventory/purchase-orders",
        {
            "supplier_id": str(_SAMPLE_SUPPLIER_ID),
            "items": [
                {
                    "product_id": str(_SAMPLE_PRODUCT_ID),
                    "quantity_ordered": "5.000",
                    "unit_cost": "20000.00",
                }
            ],
        },
        201,
    ),
    ("POST", f"/api/v1/inventory/purchase-orders/{_SAMPLE_PO_ID}/receive", {}, 200),
    ("POST", f"/api/v1/inventory/purchase-orders/{_SAMPLE_PO_ID}/cancel", None, 200),
)


@pytest.mark.parametrize("method,path,payload,expected_ok", RBAC_ENDPOINTS)
async def test_procurement_rbac_matrix(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: Dict[str, Any] | None,
    expected_ok: int,
):
    """Kiểm tra WAREHOUSE/MANAGER/ADMIN được phép; STAFF/CUSTOMER bị 403; thiếu key bị 403."""
    test_app = _build_test_app()

    class _DummySession:
        pass

    async def _dummy_db():
        yield _DummySession()

    test_app.dependency_overrides[get_db] = _dummy_db

    async def _list_suppliers(self, **_kwargs):
        return SupplierListResponse(items=[], total=0, page=1, limit=20, pages=0)

    async def _get_supplier(self, supplier_id):
        return _sample_supplier_dto()

    async def _create_supplier(self, payload):
        return _sample_supplier_dto()

    async def _update_supplier(self, supplier_id, payload):
        return _sample_supplier_dto()

    async def _list_pos(self, **_kwargs):
        return PurchaseOrderListResponse(items=[], total=0, page=1, limit=20, pages=0)

    async def _get_po(self, po_id):
        return _sample_po_dto()

    async def _create_po(self, payload, actor, request_id=None):
        return _sample_po_dto()

    async def _receive_po(self, po_id, actor, payload=None, request_id=None):
        return PurchaseOrderReceiveResponse(
            purchase_order=_sample_po_dto(),
            created_lots=[],
            created_movements=[],
        )

    async def _cancel_po(self, po_id, actor):
        return _sample_po_dto()

    monkeypatch.setattr(ProcurementService, "list_suppliers", _list_suppliers)
    monkeypatch.setattr(ProcurementService, "get_supplier", _get_supplier)
    monkeypatch.setattr(ProcurementService, "create_supplier", _create_supplier)
    monkeypatch.setattr(ProcurementService, "update_supplier", _update_supplier)
    monkeypatch.setattr(ProcurementService, "list_purchase_orders", _list_pos)
    monkeypatch.setattr(ProcurementService, "get_purchase_order", _get_po)
    monkeypatch.setattr(ProcurementService, "create_purchase_order", _create_po)
    monkeypatch.setattr(ProcurementService, "receive_purchase_order", _receive_po)
    monkeypatch.setattr(ProcurementService, "cancel_purchase_order", _cancel_po)

    user_id = str(uuid4())
    internal_header = {"X-Internal-Key": settings.INTERNAL_API_KEY}

    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://testserver"
        ) as client:
            # Thiếu X-Internal-Key -> 403 FORBIDDEN_DIRECT_ACCESS
            no_key = await client.request(method, path, json=payload)
            assert no_key.status_code == 403
            assert no_key.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"

            # Thiếu user header -> 401 UNAUTHORIZED
            no_user = await client.request(
                method, path, json=payload, headers=internal_header
            )
            assert no_user.status_code == 401
            assert no_user.json()["code"] == "UNAUTHORIZED"

            # WAREHOUSE, MANAGER, ADMIN -> thành công
            for allowed_role in ("WAREHOUSE", "MANAGER", "ADMIN"):
                ok_resp = await client.request(
                    method,
                    path,
                    json=payload,
                    headers={
                        **internal_header,
                        "X-User-Id": user_id,
                        "X-User-Role": allowed_role,
                    },
                )
                assert ok_resp.status_code == expected_ok, (
                    f"{method} {path} với role {allowed_role} thất bại: {ok_resp.text}"
                )

            # STAFF, CUSTOMER -> 403 FORBIDDEN
            for denied_role in ("STAFF", "CUSTOMER"):
                denied = await client.request(
                    method,
                    path,
                    json=payload,
                    headers={
                        **internal_header,
                        "X-User-Id": user_id,
                        "X-User-Role": denied_role,
                    },
                )
                assert denied.status_code == 403, (
                    f"{method} {path} phải chặn role {denied_role}"
                )
                assert denied.json()["code"] == "FORBIDDEN"
    finally:
        test_app.dependency_overrides.clear()
