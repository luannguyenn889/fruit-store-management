"""
Module: tests.test_lots_rbac (Inventory Service)
Nhiệm vụ: Kiểm thử ma trận phân quyền RBAC (Mục 3.13 / NFR-S03) cho toàn bộ
          11 endpoint của TV3 trong `app.api.v1.lots`:
          - Nhóm đọc (`GET`): `WAREHOUSE`, `MANAGER`, `STAFF`, `ADMIN` được phép (`200`);
            `CUSTOMER` bị từ chối (`403 FORBIDDEN`).
          - Nhóm ghi (`POST`): `WAREHOUSE`, `MANAGER`, `ADMIN` được phép (`200`);
            `STAFF`, `CUSTOMER` bị từ chối (`403 FORBIDDEN`).
          - Thiếu/sai `X-Internal-Key` -> `403 FORBIDDEN_DIRECT_ACCESS`.
          - Thiếu `X-User-Id` hoặc `X-User-Role` -> `401 UNAUTHORIZED`.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Tuple
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
import pytest

from app.core.config import settings
from app.db.session import get_db
from app.main import app as inventory_app
from app.schemas.lot import (
    ExpireOverdueResponse,
    ExpiringLotsResponse,
    LotListResponse,
    LotResponse,
    ReservationResponse,
    StockMovementListResponse,
    StockSummaryResponse,
)
from app.services.lot_service import LotService

_SAMPLE_LOT_ID = UUID("11111111-1111-1111-1111-111111111111")
_SAMPLE_RES_ID = UUID("22222222-2222-2222-2222-222222222222")
_SAMPLE_PROD_ID = UUID("33333333-3333-3333-3333-333333333333")
_SAMPLE_ORDER_ID = UUID("44444444-4444-4444-4444-444444444444")


class _DummyAsyncSession:
    """Session giả lập để cô lập tầng kiểm tra RBAC khỏi DB thật."""


async def _override_dummy_db():
    yield _DummyAsyncSession()


def _sample_lot_response() -> LotResponse:
    now = datetime.now(timezone.utc)
    return LotResponse(
        id=_SAMPLE_LOT_ID,
        lot_code="LOT-TEST-001",
        product_id=_SAMPLE_PROD_ID,
        supplier_id=None,
        purchase_order_id=None,
        quantity_received=Decimal("10.000"),
        quantity_remaining=Decimal("10.000"),
        quantity_reserved=Decimal("0.000"),
        available_quantity=Decimal("10.000"),
        unit_cost=Decimal("25000.00"),
        received_date=date.today(),
        expiry_date=date.today(),
        status="NEAR_EXPIRY",
        days_until_expiry=0,
        is_expired=False,
        created_at=now,
        updated_at=now,
    )


def _sample_reservation_response() -> ReservationResponse:
    now = datetime.now(timezone.utc)
    return ReservationResponse(
        id=_SAMPLE_RES_ID,
        order_id=_SAMPLE_ORDER_ID,
        idempotency_key="idem-rbac-001",
        status="ACTIVE",
        expires_at=now,
        created_at=now,
        items=[],
    )


@pytest.fixture(autouse=True)
def _stub_lot_service_and_db(monkeypatch: pytest.MonkeyPatch):
    """Stub DB và LotService để test đúng tầng dependency RBAC của từng route."""
    inventory_app.dependency_overrides[get_db] = _override_dummy_db

    async def _get_stock_summary(self, product_id=None):
        return StockSummaryResponse(
            total_products=0,
            total_available_quantity=Decimal("0.000"),
            total_reserved_quantity=Decimal("0.000"),
            total_remaining_quantity=Decimal("0.000"),
            products=[],
        )

    async def _get_expiring_lots(self, days=3):
        return ExpiringLotsResponse(
            days_threshold=days,
            total_near_expiry=0,
            total_expired=0,
            near_expiry_lots=[],
            expired_lots=[],
        )

    async def _list_lots(self, product_id=None, status=None, page=1, limit=20):
        return LotListResponse(items=[], total=0, page=page, limit=limit, pages=0)

    async def _get_lot_by_id(self, lot_id):
        return _sample_lot_response()

    async def _list_movements(self, **_kwargs):
        return StockMovementListResponse(items=[], total=0, page=1, limit=20, pages=0)

    async def _record_wastage(self, lot_id, req, actor=None):
        return _sample_lot_response()

    async def _adjust_stock(self, lot_id, req, actor=None):
        return _sample_lot_response()

    async def _expire_overdue(self):
        return ExpireOverdueResponse(
            expired_count=0,
            expired_reservation_ids=[],
            message="OK",
        )

    async def _create_reservation(self, req, actor=None):
        return _sample_reservation_response()

    async def _commit_reservation(self, reservation_id, actor=None):
        return _sample_reservation_response()

    async def _release_reservation(self, reservation_id, actor=None):
        return _sample_reservation_response()

    monkeypatch.setattr(LotService, "get_stock_summary", _get_stock_summary)
    monkeypatch.setattr(LotService, "get_expiring_lots", _get_expiring_lots)
    monkeypatch.setattr(LotService, "list_lots", _list_lots)
    monkeypatch.setattr(LotService, "get_lot_by_id", _get_lot_by_id)
    monkeypatch.setattr(LotService, "list_movements", _list_movements)
    monkeypatch.setattr(LotService, "record_wastage", _record_wastage)
    monkeypatch.setattr(LotService, "adjust_stock", _adjust_stock)
    monkeypatch.setattr(LotService, "expire_overdue_reservations", _expire_overdue)
    monkeypatch.setattr(LotService, "create_reservation", _create_reservation)
    monkeypatch.setattr(LotService, "commit_reservation", _commit_reservation)
    monkeypatch.setattr(LotService, "release_reservation", _release_reservation)

    yield
    inventory_app.dependency_overrides.clear()


READ_ENDPOINTS: Tuple[Tuple[str, str], ...] = (
    ("GET", "/api/v1/inventory/stock/summary"),
    ("GET", "/api/v1/inventory/lots/expiring"),
    ("GET", "/api/v1/inventory/lots"),
    ("GET", f"/api/v1/inventory/lots/{_SAMPLE_LOT_ID}"),
    ("GET", "/api/v1/inventory/movements"),
)

WRITE_ENDPOINTS: Tuple[Tuple[str, str, Dict[str, Any]], ...] = (
    (
        "POST",
        f"/api/v1/inventory/lots/{_SAMPLE_LOT_ID}/wastage",
        {"quantity": "1.000", "reason_type": "WASTE_DAMAGED", "note": "Bị dập"},
    ),
    (
        "POST",
        f"/api/v1/inventory/lots/{_SAMPLE_LOT_ID}/adjust",
        {"actual_quantity": "8.000", "reason": "Kiểm kê cuối ngày"},
    ),
    ("POST", "/api/v1/inventory/reservations/expire-overdue", {}),
    (
        "POST",
        "/api/v1/inventory/reservations",
        {
            "order_id": str(_SAMPLE_ORDER_ID),
            "idempotency_key": "idem-rbac-001",
            "items": [{"product_id": str(_SAMPLE_PROD_ID), "quantity": "1.000"}],
        },
    ),
    ("POST", f"/api/v1/inventory/reservations/{_SAMPLE_RES_ID}/commit", {}),
    ("POST", f"/api/v1/inventory/reservations/{_SAMPLE_RES_ID}/release", {}),
)


@pytest.mark.parametrize("method,path", READ_ENDPOINTS)
async def test_read_endpoints_rbac(method: str, path: str):
    """Kiểm tra nhóm GET: WAREHOUSE/MANAGER/STAFF/ADMIN -> 200; CUSTOMER -> 403."""
    user_id = str(uuid4())
    internal_header = {"X-Internal-Key": settings.INTERNAL_API_KEY}

    async with AsyncClient(
        transport=ASGITransport(app=inventory_app), base_url="http://testserver"
    ) as client:
        # Thiếu internal key -> 403
        no_key = await client.request(method, path)
        assert no_key.status_code == 403
        assert no_key.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"

        # Thiếu user header -> 401
        no_user = await client.request(method, path, headers=internal_header)
        assert no_user.status_code == 401
        assert no_user.json()["code"] == "UNAUTHORIZED"

        # Các role được đọc
        for allowed in ("WAREHOUSE", "MANAGER", "STAFF", "ADMIN"):
            resp = await client.request(
                method,
                path,
                headers={**internal_header, "X-User-Id": user_id, "X-User-Role": allowed},
            )
            assert resp.status_code == 200, f"{method} {path} với role {allowed} thất bại"

        # CUSTOMER bị từ chối
        forbidden = await client.request(
            method,
            path,
            headers={**internal_header, "X-User-Id": user_id, "X-User-Role": "CUSTOMER"},
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method,path,payload", WRITE_ENDPOINTS)
async def test_write_endpoints_rbac(method: str, path: str, payload: Dict[str, Any]):
    """Kiểm tra nhóm POST: WAREHOUSE/MANAGER/ADMIN -> 200; STAFF/CUSTOMER -> 403."""
    user_id = str(uuid4())
    internal_header = {"X-Internal-Key": settings.INTERNAL_API_KEY}

    async with AsyncClient(
        transport=ASGITransport(app=inventory_app), base_url="http://testserver"
    ) as client:
        # Thiếu internal key -> 403
        no_key = await client.request(method, path, json=payload)
        assert no_key.status_code == 403
        assert no_key.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"

        # Thiếu user header -> 401
        no_user = await client.request(method, path, json=payload, headers=internal_header)
        assert no_user.status_code == 401
        assert no_user.json()["code"] == "UNAUTHORIZED"

        # Các role được ghi
        for allowed in ("WAREHOUSE", "MANAGER", "ADMIN"):
            resp = await client.request(
                method,
                path,
                json=payload,
                headers={**internal_header, "X-User-Id": user_id, "X-User-Role": allowed},
            )
            assert resp.status_code == 200, f"{method} {path} với role {allowed} thất bại"

        # STAFF và CUSTOMER bị từ chối
        for denied in ("STAFF", "CUSTOMER"):
            resp = await client.request(
                method,
                path,
                json=payload,
                headers={**internal_header, "X-User-Id": user_id, "X-User-Role": denied},
            )
            assert resp.status_code == 403, f"{method} {path} phải chặn role {denied}"
            assert resp.json()["code"] == "FORBIDDEN"
