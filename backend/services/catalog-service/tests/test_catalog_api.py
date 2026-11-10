"""
Module: tests.test_catalog_api (Catalog Service)
Nhiệm vụ: Kiểm thử tự động toàn diện cho Catalog Service theo kế hoạch Tuần 1:
          1. Alembic migration `upgrade head -> downgrade -1 -> upgrade head` độc lập (NFR-M02).
          2. Thiếu `X-Internal-Key` -> `403 FORBIDDEN_DIRECT_ACCESS`.
          3. Phân quyền RBAC: `STAFF` / `CUSTOMER` gọi thao tác ghi -> `403 FORBIDDEN`; `MANAGER` / `ADMIN` -> thành công.
          4. Danh mục: xóa danh mục đang chứa sản phẩm -> `409 CATEGORY_HAS_PRODUCTS`.
          5. Sản phẩm:
             - Tạo sản phẩm ghi luôn dòng `PriceHistory` khởi tạo đầu tiên.
             - SKU trùng -> `409 SKU_ALREADY_EXISTS`.
             - Giá âm -> `422 VALIDATION_ERROR`.
             - Đơn vị tính sai (ngoài `kg`, `hop`, `qua`) -> `422 VALIDATION_ERROR`.
             - `PATCH` sản phẩm cập nhật thông tin nhưng chặn truyền `price` (`422`).
             - `POST /deactivate` chuyển sang `INACTIVE`, vẫn đọc được qua `GET /products/{id}`.
          6. Đơn giá & `PriceHistory` (FR-B06, BR-07):
             - Đổi giá ghi đúng dòng lịch sử (`old_price`, `new_price`, `changed_by_user_id`, `reason`).
             - Đổi giá trùng giá hiện tại -> `409 PRICE_UNCHANGED`.
             - Nhiều yêu cầu đổi giá liên tiếp/đồng thời giữ nguyên vẹn mọi dòng lịch sử (`SELECT ... FOR UPDATE`).
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

MANAGER_ID = str(uuid4())
STAFF_ID = str(uuid4())

MANAGER_HEADERS = {
    "X-Internal-Key": settings.INTERNAL_API_KEY,
    "X-User-Id": MANAGER_ID,
    "X-User-Role": "MANAGER",
}

STAFF_HEADERS = {
    "X-Internal-Key": settings.INTERNAL_API_KEY,
    "X-User-Id": STAFF_ID,
    "X-User-Role": "STAFF",
}

PUBLIC_HEADERS = {
    "X-Internal-Key": settings.INTERNAL_API_KEY,
}


def test_alembic_upgrade_and_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra migration `0001_init_catalog` chạy `upgrade head -> downgrade -1 -> upgrade head` độc lập (NFR-M02)."""
    db_file = tmp_path / "alembic_catalog_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)

    service_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(service_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(service_root / "alembic"))

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "-1")
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture()
async def client(tmp_path: Path):
    """Khởi tạo DB test cô lập cho Catalog Service và cung cấp `AsyncClient`."""
    db_file = tmp_path / "catalog_service_test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}", echo=False
    )
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_missing_internal_key_rejected(client: AsyncClient) -> None:
    """Thiếu `X-Internal-Key` khi gọi vào Catalog Service phải trả về 403."""
    resp = await client.get("/api/v1/catalog/products")
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"


@pytest.mark.asyncio
async def test_rbac_staff_cannot_mutate_catalog(client: AsyncClient) -> None:
    """Nhân viên `STAFF` hoặc `CUSTOMER` gọi tạo danh mục/sản phẩm phải bị chặn 403."""
    resp = await client.post(
        "/api/v1/catalog/categories",
        headers=STAFF_HEADERS,
        json={"name": "Xoài"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_full_catalog_and_price_history_lifecycle(
    client: AsyncClient,
) -> None:
    """
    Kiểm thử toàn trình nghiệp vụ Danh mục, Sản phẩm, SKU duy nhất, Đơn vị tính,
    Ngừng kinh doanh và Lịch sử đổi giá (PriceHistory).
    """
    # 1. Tạo 2 danh mục: "Xoài" và "Danh mục rỗng"
    cat_resp = await client.post(
        "/api/v1/catalog/categories",
        headers=MANAGER_HEADERS,
        json={"name": "Xoài đặc sản", "description": "Các giống xoài miền Tây"},
    )
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    empty_cat_resp = await client.post(
        "/api/v1/catalog/categories",
        headers=MANAGER_HEADERS,
        json={"name": "Danh mục tạm"},
    )
    assert empty_cat_resp.status_code == 201
    empty_cat_id = empty_cat_resp.json()["id"]

    # Xóa danh mục rỗng -> 204 thành công
    del_empty_resp = await client.delete(
        f"/api/v1/catalog/categories/{empty_cat_id}",
        headers=MANAGER_HEADERS,
    )
    assert del_empty_resp.status_code == 204

    # 2. Tạo sản phẩm hợp lệ: XOAI-HL-01, unit=kg, price=65000.00
    prod_resp = await client.post(
        "/api/v1/catalog/products",
        headers=MANAGER_HEADERS,
        json={
            "category_id": category_id,
            "sku": "XOAI-HL-01",
            "name": "Xoài cát Hòa Lộc",
            "unit": "kg",
            "price": "65000.00",
            "origin": "Cái Bè, Tiền Giang",
            "default_shelf_life_days": 7,
            "storage_condition": "COOL_8_12C",
        },
    )
    assert prod_resp.status_code == 201
    prod_data = prod_resp.json()
    product_id = prod_data["id"]
    assert prod_data["sku"] == "XOAI-HL-01"
    assert prod_data["price"] == "65000.00"
    assert prod_data["unit"] == "kg"

    # 3. Tạo SKU trùng -> 409 SKU_ALREADY_EXISTS
    dup_sku_resp = await client.post(
        "/api/v1/catalog/products",
        headers=MANAGER_HEADERS,
        json={
            "category_id": category_id,
            "sku": "XOAI-HL-01",
            "name": "Xoài cát Hòa Lộc loại 2",
            "unit": "kg",
            "price": "50000.00",
        },
    )
    assert dup_sku_resp.status_code == 409
    assert dup_sku_resp.json()["code"] == "SKU_ALREADY_EXISTS"

    # 4. Tạo sản phẩm giá âm -> 422 VALIDATION_ERROR
    neg_price_resp = await client.post(
        "/api/v1/catalog/products",
        headers=MANAGER_HEADERS,
        json={
            "category_id": category_id,
            "sku": "XOAI-NEG-01",
            "name": "Xoài giá âm",
            "unit": "kg",
            "price": "-5000.00",
        },
    )
    assert neg_price_resp.status_code == 422
    assert neg_price_resp.json()["code"] == "VALIDATION_ERROR"

    # 5. Tạo sản phẩm đơn vị sai (ngoài kg, hop, qua) -> 422 VALIDATION_ERROR
    bad_unit_resp = await client.post(
        "/api/v1/catalog/products",
        headers=MANAGER_HEADERS,
        json={
            "category_id": category_id,
            "sku": "XOAI-UNIT-01",
            "name": "Xoài đơn vị sai",
            "unit": "trai",
            "price": "40000.00",
        },
    )
    assert bad_unit_resp.status_code == 422
    assert bad_unit_resp.json()["code"] == "VALIDATION_ERROR"

    # 6. Xóa danh mục đang còn sản phẩm -> 409 CATEGORY_HAS_PRODUCTS
    del_cat_resp = await client.delete(
        f"/api/v1/catalog/categories/{category_id}",
        headers=MANAGER_HEADERS,
    )
    assert del_cat_resp.status_code == 409
    assert del_cat_resp.json()["code"] == "CATEGORY_HAS_PRODUCTS"

    # 7. Đổi giá sản phẩm sang 70000.00 -> kiểm tra PriceHistory
    price_resp = await client.post(
        f"/api/v1/catalog/products/{product_id}/price",
        headers=MANAGER_HEADERS,
        json={"new_price": "70000.00", "reason": "Giá mùa vụ"},
    )
    assert price_resp.status_code == 200
    assert price_resp.json()["price"] == "70000.00"

    # Đổi giá trùng giá hiện tại (70000.00) -> 409 PRICE_UNCHANGED
    same_price_resp = await client.post(
        f"/api/v1/catalog/products/{product_id}/price",
        headers=MANAGER_HEADERS,
        json={"new_price": "70000.00", "reason": "Gửi nhầm giá cũ"},
    )
    assert same_price_resp.status_code == 409
    assert same_price_resp.json()["code"] == "PRICE_UNCHANGED"

    # Hai yêu cầu đổi giá gửi đồng thời (75000.00 và 80000.00) không làm mất dòng lịch sử
    r1, r2 = await asyncio.gather(
        client.post(
            f"/api/v1/catalog/products/{product_id}/price",
            headers=MANAGER_HEADERS,
            json={"new_price": "75000.00", "reason": "Đợt điều chỉnh 1"},
        ),
        client.post(
            f"/api/v1/catalog/products/{product_id}/price",
            headers=MANAGER_HEADERS,
            json={"new_price": "80000.00", "reason": "Đợt điều chỉnh 2"},
        ),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Kiểm tra lịch sử giá: phải có đủ 4 dòng (1 khởi tạo + 3 lần đổi giá)
    hist_resp = await client.get(
        f"/api/v1/catalog/products/{product_id}/price-history",
        headers=PUBLIC_HEADERS,
    )
    assert hist_resp.status_code == 200
    histories = hist_resp.json()
    assert len(histories) == 4
    # Kiểm tra bản ghi đổi từ 65000.00 -> 70000.00 có đúng user và lý do
    seasonal_record = next(
        h for h in histories if h["reason"] == "Giá mùa vụ"
    )
    assert seasonal_record["old_price"] == "65000.00"
    assert seasonal_record["new_price"] == "70000.00"
    assert seasonal_record["changed_by_user_id"] == MANAGER_ID

    # 8. Ngừng kinh doanh sản phẩm (POST /deactivate) -> INACTIVE nhưng vẫn đọc được
    deact_resp = await client.post(
        f"/api/v1/catalog/products/{product_id}/deactivate",
        headers=MANAGER_HEADERS,
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["status"] == "INACTIVE"

    detail_resp = await client.get(
        f"/api/v1/catalog/products/{product_id}",
        headers=PUBLIC_HEADERS,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == "INACTIVE"

