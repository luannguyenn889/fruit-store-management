"""
Module: tests.e2e.test_catalog_via_gateway
Nhiệm vụ: Kiểm thử tích hợp đầu-cuối (End-to-End Test) đi xuyên qua API Gateway (:8000)
          tới Auth Service (:8001, `fruitstore_auth_db`) và Catalog Service (:8002, `fruitstore_catalog_db`).
          Kiểm tra đầy đủ 7 kịch bản trong Kế hoạch Tuần 1:
          1. Đăng nhập `manager@fruitstore.com` qua Gateway -> nhận JWT 30 phút.
          2. Tạo danh mục "Xoài", tạo sản phẩm `XOAI-HL-01`, `unit=kg`, `price=65000.00`.
          3. Tạo SKU trùng -> `409 SKU_ALREADY_EXISTS`.
          4. Đổi giá `70000.00` -> `GET price-history` có bản ghi `65000.00 -> 70000.00` và `changed_by_user_id` khớp.
          5. Đăng nhập `staff@fruitstore.com` -> `POST /products` bị `403`; không token -> `POST` bị `401`;
             `GET /products` không token -> `200 OK`.
          6. Giả mạo header `X-User-Role: ADMIN` từ phía client -> Gateway tự động xóa và ghi đè từ JWT, vẫn bị `403`.
          7. Cô lập lỗi (NFR-R03): Khi `catalog-service` ngừng phản hồi -> Gateway trả `502 UPSTREAM_UNAVAILABLE`,
             nhưng `auth-service` vẫn đăng nhập bình thường.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def load_service_app(service_dir: Path, alias_prefix: str) -> FastAPI:
    """
    Nạp độc lập một FastAPI app từ thư mục service (`gateway`, `auth-service`, `catalog-service`)
    để chạy kiểm thử E2E đa tiến trình/đa cơ sở dữ liệu ngay trong bộ nhớ mà không lẫn module `app.*`.
    """
    saved_modules: Dict[str, object] = {}
    for mod_name in list(sys.modules.keys()):
        if mod_name == "app" or mod_name.startswith("app."):
            saved_modules[mod_name] = sys.modules.pop(mod_name)

    sys.path.insert(0, str(service_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            f"{alias_prefix}_main", service_dir / "app" / "main.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Lưu bản sao các module của service dưới tiền tố riêng
        service_modules = {
            k: v
            for k, v in sys.modules.items()
            if k == "app" or k.startswith("app.")
        }
        return module.app, service_modules  # type: ignore[return-value]
    finally:
        sys.path.remove(str(service_dir))
        for mod_name in list(sys.modules.keys()):
            if mod_name == "app" or mod_name.startswith("app."):
                sys.modules.pop(mod_name, None)
        sys.modules.update(saved_modules)  # type: ignore[arg-type]


class MultiServiceRouterTransport(httpx.AsyncBaseTransport):
    """
    Bộ định tuyến HTTP nội bộ dùng cho `gateway.state.http_client`:
    - Request tới `http://localhost:8001` -> chuyển vào `auth-service` (kết nối `auth_db` riêng).
    - Request tới `http://localhost:8002` -> chuyển vào `catalog-service` (kết nối `catalog_db` riêng).
    - Hỗ trợ giả lập trạng thái `catalog_down = True` để kiểm thử lỗi `502 UPSTREAM_UNAVAILABLE`.
    """

    def __init__(self, auth_app: FastAPI, catalog_app: FastAPI) -> None:
        self.auth_transport = ASGITransport(app=auth_app)
        self.catalog_transport = ASGITransport(app=catalog_app)
        self.catalog_down = False

    async def handle_async_request(
        self, request: httpx.Request
    ) -> httpx.Response:
        port = request.url.port
        if port == 8001:
            return await self.auth_transport.handle_async_request(request)
        if port == 8002:
            if self.catalog_down:
                raise httpx.ConnectError(
                    "Connection refused to catalog-service :8002",
                    request=request,
                )
            return await self.catalog_transport.handle_async_request(request)
        raise httpx.ConnectError(f"Unknown upstream port: {port}", request=request)


@pytest_asyncio.fixture()
async def e2e_env(tmp_path: Path):
    """
    Thiết lập môi trường E2E chuẩn SOA gồm:
    - `auth_db` riêng biệt (SQLite độc lập 1) cho `auth-service`.
    - `catalog_db` riêng biệt (SQLite độc lập 2) cho `catalog-service`.
    - `gateway_app` định tuyến qua `MultiServiceRouterTransport`.
    """
    auth_dir = BACKEND_ROOT / "services" / "auth-service"
    catalog_dir = BACKEND_ROOT / "services" / "catalog-service"
    gateway_dir = BACKEND_ROOT / "gateway"

    auth_app, auth_mods = load_service_app(auth_dir, "auth")
    catalog_app, catalog_mods = load_service_app(catalog_dir, "catalog")
    gateway_app, _ = load_service_app(gateway_dir, "gateway")

    # 1. Khởi tạo DB độc lập cho Auth Service
    auth_db_path = tmp_path / "fruitstore_auth_e2e.db"
    auth_engine = create_async_engine(
        f"sqlite+aiosqlite:///{auth_db_path.as_posix()}", echo=False
    )
    auth_session_factory = async_sessionmaker(
        bind=auth_engine, class_=AsyncSession, expire_on_commit=False
    )
    auth_base = auth_mods["app.db.base"].Base  # type: ignore[attr-defined]
    auth_get_db = auth_mods["app.db.session"].get_db  # type: ignore[attr-defined]

    # Nạp hàm seed của Auth Service
    sys.modules.update(auth_mods)  # type: ignore[arg-type]
    sys.path.insert(0, str(auth_dir))
    try:
        from app.scripts.seed import seed_auth_data  # type: ignore[import-not-found]
    finally:
        sys.path.remove(str(auth_dir))
        for k in list(auth_mods.keys()):
            sys.modules.pop(k, None)

    async with auth_engine.begin() as conn:
        await conn.run_sync(auth_base.metadata.create_all)
    async with auth_session_factory() as session:
        await seed_auth_data(session)

    async def override_auth_db():
        async with auth_session_factory() as s:
            yield s

    auth_app.dependency_overrides[auth_get_db] = override_auth_db

    # 2. Khởi tạo DB độc lập cho Catalog Service
    catalog_db_path = tmp_path / "fruitstore_catalog_e2e.db"
    catalog_engine = create_async_engine(
        f"sqlite+aiosqlite:///{catalog_db_path.as_posix()}", echo=False
    )
    catalog_session_factory = async_sessionmaker(
        bind=catalog_engine, class_=AsyncSession, expire_on_commit=False
    )
    catalog_base = catalog_mods["app.db.base"].Base  # type: ignore[attr-defined]
    catalog_get_db = catalog_mods["app.db.session"].get_db  # type: ignore[attr-defined]

    async with catalog_engine.begin() as conn:
        await conn.run_sync(catalog_base.metadata.create_all)

    async def override_catalog_db():
        async with catalog_session_factory() as s:
            yield s

    catalog_app.dependency_overrides[catalog_get_db] = override_catalog_db

    # 3. Gắn Router Transport vào Gateway
    router_transport = MultiServiceRouterTransport(auth_app, catalog_app)
    upstream_client = AsyncClient(transport=router_transport)
    gateway_app.state.http_client = upstream_client

    gw_transport = ASGITransport(app=gateway_app)
    async with AsyncClient(
        transport=gw_transport, base_url="http://localhost:8000"
    ) as gw_client:
        yield gw_client, router_transport

    await upstream_client.aclose()
    await auth_engine.dispose()
    await catalog_engine.dispose()


@pytest.mark.asyncio
async def test_e2e_catalog_and_auth_via_gateway(e2e_env) -> None:
    """Kiểm thử toàn bộ luồng E2E từ Gateway -> Auth Service & Catalog Service."""
    gw_client, router_transport = e2e_env

    # Kịch bản 1: Đăng nhập manager@fruitstore.com qua Gateway -> lấy JWT
    login_mgr = await gw_client.post(
        "/api/v1/auth/login",
        json={"email": "manager@fruitstore.com", "password": "Manager@123"},
    )
    assert login_mgr.status_code == 200
    assert "X-Request-ID" in login_mgr.headers
    mgr_token = login_mgr.json()["access_token"]
    mgr_user_id = login_mgr.json()["user"]["id"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Kịch bản 2: Tạo danh mục "Xoài" & Tạo sản phẩm XOAI-HL-01, unit=kg, 65000.00
    cat_resp = await gw_client.post(
        "/api/v1/catalog/categories",
        headers=mgr_headers,
        json={"name": "Xoài", "description": "Xoài cát miền Tây"},
    )
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    prod_resp = await gw_client.post(
        "/api/v1/catalog/products",
        headers=mgr_headers,
        json={
            "category_id": category_id,
            "sku": "XOAI-HL-01",
            "name": "Xoài cát Hòa Lộc",
            "unit": "kg",
            "price": "65000.00",
            "origin": "Tiền Giang",
            "default_shelf_life_days": 7,
            "storage_condition": "COOL_8_12C",
        },
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    # Kịch bản 3: Tạo SKU trùng -> 409 SKU_ALREADY_EXISTS
    dup_resp = await gw_client.post(
        "/api/v1/catalog/products",
        headers=mgr_headers,
        json={
            "category_id": category_id,
            "sku": "XOAI-HL-01",
            "name": "Xoài trùng SKU",
            "unit": "kg",
            "price": "60000.00",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["code"] == "SKU_ALREADY_EXISTS"

    # Kịch bản 4: Đổi giá sang 70000.00 -> GET price-history có bản ghi 65000.00 -> 70000.00 & đúng user
    change_price_resp = await gw_client.post(
        f"/api/v1/catalog/products/{product_id}/price",
        headers=mgr_headers,
        json={"new_price": "70000.00", "reason": "Giá mùa vụ"},
    )
    assert change_price_resp.status_code == 200
    assert change_price_resp.json()["price"] == "70000.00"

    hist_resp = await gw_client.get(
        f"/api/v1/catalog/products/{product_id}/price-history"
    )
    assert hist_resp.status_code == 200
    histories = hist_resp.json()
    assert any(
        h["old_price"] == "65000.00"
        and h["new_price"] == "70000.00"
        and h["changed_by_user_id"] == mgr_user_id
        for h in histories
    )

    # Kịch bản 5: Đăng nhập staff@fruitstore.com -> POST /products bị 403;
    # không token -> POST bị 401; GET /products không token -> 200 OK
    login_staff = await gw_client.post(
        "/api/v1/auth/login",
        json={"email": "staff@fruitstore.com", "password": "Staff@123"},
    )
    assert login_staff.status_code == 200
    staff_token = login_staff.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    staff_post = await gw_client.post(
        "/api/v1/catalog/products",
        headers=staff_headers,
        json={
            "category_id": category_id,
            "sku": "TAO-01",
            "name": "Táo Fuji",
            "unit": "kg",
            "price": "85000.00",
        },
    )
    assert staff_post.status_code == 403

    no_token_post = await gw_client.post(
        "/api/v1/catalog/products",
        json={
            "category_id": category_id,
            "sku": "TAO-01",
            "name": "Táo Fuji",
            "unit": "kg",
            "price": "85000.00",
        },
    )
    assert no_token_post.status_code == 401

    public_get = await gw_client.get("/api/v1/catalog/products")
    assert public_get.status_code == 200
    assert public_get.json()["total"] == 1

    # Kịch bản 6: Client cố tình gửi header giả mạo `X-User-Role: ADMIN` kèm token của Staff ->
    # Gateway xóa sạch `X-User-*` từ client và ghi đè bằng `STAFF` từ JWT -> vẫn bị 403!
    spoof_resp = await gw_client.post(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {staff_token}",
            "X-User-Role": "ADMIN",
            "X-User-Id": mgr_user_id,
        },
        json={
            "category_id": category_id,
            "sku": "SPOOF-01",
            "name": "Sản phẩm giả mạo quyền",
            "unit": "kg",
            "price": "90000.00",
        },
    )
    assert spoof_resp.status_code == 403
    assert spoof_resp.json()["code"] == "FORBIDDEN"

    # Kịch bản 7: Cô lập lỗi từng phần (NFR-R03) — Khi catalog-service dừng,
    # gọi /api/v1/catalog/products trả 502 chuẩn, nhưng auth-service vẫn đăng nhập bình thường.
    router_transport.catalog_down = True
    down_resp = await gw_client.get("/api/v1/catalog/products")
    assert down_resp.status_code == 502
    assert down_resp.json()["code"] == "UPSTREAM_UNAVAILABLE"

    still_alive_auth = await gw_client.post(
        "/api/v1/auth/login",
        json={"email": "manager@fruitstore.com", "password": "Manager@123"},
    )
    assert still_alive_auth.status_code == 200

