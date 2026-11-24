"""
Module: tests.test_health_and_deps (Inventory Service)
Nhiệm vụ: Kiểm thử khói (Smoke Tests) cho khung nền tảng của Thành viên 1:
          - `GET /health` và `GET /api/v1/inventory/health` trả `200` khi DB sẵn sàng,
            trả `503 DB_UNAVAILABLE` khi DB lỗi, đồng thời phản hồi `X-Request-ID`.
          - `verify_internal_key` từ chối request thiếu/sai `X-Internal-Key` (`403`).
          - `require_roles` kiểm soát RBAC (`WAREHOUSE`, `MANAGER`, `ADMIN` vs `STAFF`, `CUSTOMER`).
          - Xác nhận đủ 7 bảng trong `Base.metadata` và không có cột kiểu `Float` (NFR-K04).
"""

from uuid import uuid4

from fastapi import Depends
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import Float

import app.models as _inventory_models  # noqa: F401 - Nạp đầy đủ ORM models trước khi kiểm tra metadata
from app.core.config import settings
from app.core.deps import Actor, require_roles, verify_internal_key
from app.db.base import Base
from app.db.session import get_db
from app.main import app as inventory_app


class _HealthyFakeSession:
    async def execute(self, _stmt):
        return 1


class _BrokenFakeSession:
    async def execute(self, _stmt):
        raise ConnectionError("PostgreSQL connection refused")


async def _override_healthy_db():
    yield _HealthyFakeSession()


async def _override_broken_db():
    yield _BrokenFakeSession()


@inventory_app.get("/_test/internal-only", dependencies=[Depends(verify_internal_key)])
async def _probe_internal_only():
    return {"ok": True}


@inventory_app.get(
    "/_test/warehouse-only",
    dependencies=[Depends(verify_internal_key)],
)
async def _probe_warehouse_only(
    actor: Actor = Depends(require_roles("WAREHOUSE", "MANAGER")),
):
    return {"actor_id": str(actor.id), "role": actor.role}


async def test_health_endpoints_return_200_and_echo_request_id():
    """Kiểm tra `/health` và `/api/v1/inventory/health` trả 200 và giữ `X-Request-ID`."""
    inventory_app.dependency_overrides[get_db] = _override_healthy_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=inventory_app), base_url="http://testserver"
        ) as client:
            resp = await client.get("/health", headers={"X-Request-ID": "req-inv-001"})
            assert resp.status_code == 200
            assert resp.headers.get("X-Request-ID") == "req-inv-001"
            assert resp.json() == {
                "status": "healthy",
                "service": "inventory-service",
                "database": "fruitstore_inventory_db",
            }

            gw_resp = await client.get("/api/v1/inventory/health")
            assert gw_resp.status_code == 200
            assert gw_resp.headers.get("X-Request-ID")
            assert gw_resp.json()["service"] == "inventory-service"
    finally:
        inventory_app.dependency_overrides.clear()


async def test_health_endpoint_returns_503_when_db_unavailable():
    """Kiểm tra `/health` trả `503 DB_UNAVAILABLE` khi DB gặp sự cố."""
    inventory_app.dependency_overrides[get_db] = _override_broken_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=inventory_app), base_url="http://testserver"
        ) as client:
            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["code"] == "DB_UNAVAILABLE"
    finally:
        inventory_app.dependency_overrides.clear()


async def test_verify_internal_key_blocks_direct_access():
    """Kiểm tra thiếu hoặc sai `X-Internal-Key` bị từ chối với mã `403`."""
    async with AsyncClient(
        transport=ASGITransport(app=inventory_app), base_url="http://testserver"
    ) as client:
        missing = await client.get("/_test/internal-only")
        assert missing.status_code == 403
        assert missing.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"

        wrong = await client.get(
            "/_test/internal-only", headers={"X-Internal-Key": "wrong-key"}
        )
        assert wrong.status_code == 403
        assert wrong.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"

        ok = await client.get(
            "/_test/internal-only",
            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
        )
        assert ok.status_code == 200


async def test_require_roles_rbac_matrix():
    """Kiểm tra phân quyền RBAC trên header `X-User-Id` & `X-User-Role` từ Gateway."""
    user_id = str(uuid4())
    valid_key = {"X-Internal-Key": settings.INTERNAL_API_KEY}

    async with AsyncClient(
        transport=ASGITransport(app=inventory_app), base_url="http://testserver"
    ) as client:
        unauth = await client.get("/_test/warehouse-only", headers=valid_key)
        assert unauth.status_code == 401

        for allowed in ("WAREHOUSE", "MANAGER", "ADMIN"):
            res = await client.get(
                "/_test/warehouse-only",
                headers={**valid_key, "X-User-Id": user_id, "X-User-Role": allowed},
            )
            assert res.status_code == 200
            assert res.json()["role"] == allowed

        for forbidden in ("STAFF", "CUSTOMER"):
            res = await client.get(
                "/_test/warehouse-only",
                headers={**valid_key, "X-User-Id": user_id, "X-User-Role": forbidden},
            )
            assert res.status_code == 403
            assert res.json()["code"] == "FORBIDDEN"


def test_models_schema_has_7_tables_and_no_float_columns():
    """Xác nhận `Base.metadata` có đủ 7 bảng và tuyệt đối không dùng kiểu `Float` (NFR-K04)."""
    expected_tables = {
        "suppliers",
        "purchase_orders",
        "purchase_items",
        "stock_lots",
        "reservations",
        "reservation_items",
        "stock_movements",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))

    for table_name in expected_tables:
        table = Base.metadata.tables[table_name]
        for col in table.columns:
            assert not isinstance(col.type, Float), (
                f"Cột {table_name}.{col.name} vi phạm NFR-K04 khi sử dụng Float."
            )
