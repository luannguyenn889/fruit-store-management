"""
Module: tests.test_auth_api (Auth Service)
Nhiệm vụ: Kiểm thử tự động (Unit & API Tests) cho Auth Service:
          1. Kiểm thử Alembic migration `upgrade head -> downgrade -1 -> upgrade head` độc lập (NFR-M02).
          2. Kiểm thử chặn truy cập trực tiếp khi thiếu `X-Internal-Key` (`403 FORBIDDEN_DIRECT_ACCESS`).
          3. Kiểm thử đăng ký tài khoản (`POST /api/v1/auth/register`): luôn gán cố định vai trò `CUSTOMER`,
             từ chối email trùng lặp (`409 EMAIL_ALREADY_EXISTS`).
          4. Kiểm thử đăng nhập (`POST /api/v1/auth/login`): trả về JWT có `sub`, `role`, thời hạn 30 phút (`1800s`).
          5. Kiểm thử bảo mật Google OAuth2 (`POST /api/v1/auth/google`): từ chối token giả mạo (`401 INVALID_GOOGLE_TOKEN`)
             và cấp JWT khi `google-auth` xác thực chữ ký thành công.
"""

from pathlib import Path
from unittest.mock import patch

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
from app.scripts.seed import seed_auth_data

INTERNAL_HEADERS = {"X-Internal-Key": settings.INTERNAL_API_KEY}


def test_alembic_upgrade_and_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra migration `0001_init_auth` chạy `upgrade head -> downgrade -1 -> upgrade head` độc lập (NFR-M02)."""
    db_file = tmp_path / "alembic_auth_test.db"
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
    """Khởi tạo cơ sở dữ liệu test cô lập, chạy seed 5 vai trò + tài khoản mẫu và trả về `AsyncClient`."""
    db_file = tmp_path / "auth_service_test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}", echo=False
    )
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await seed_auth_data(session)

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
async def test_reject_direct_call_without_internal_key(client: AsyncClient) -> None:
    """Gọi thẳng vào Auth Service mà không có `X-Internal-Key` phải bị chặn với 403."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@fruitstore.com", "password": settings.SEED_MANAGER_PASSWORD},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN_DIRECT_ACCESS"


@pytest.mark.asyncio
async def test_register_always_assigns_customer_role(client: AsyncClient) -> None:
    """Đăng ký tài khoản mới luôn nhận vai trò `CUSTOMER` và chặn trùng email (409)."""
    resp = await client.post(
        "/api/v1/auth/register",
        headers=INTERNAL_HEADERS,
        json={
            "email": "khachhang@fruitstore.com",
            "phone": "0918234889",
            "full_name": "Nguyễn Thị Khách",
            "password": "Password@123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "khachhang@fruitstore.com"
    assert [r["code"] for r in data["roles"]] == ["CUSTOMER"]

    # Đăng ký trùng email -> 409 EMAIL_ALREADY_EXISTS
    dup_resp = await client.post(
        "/api/v1/auth/register",
        headers=INTERNAL_HEADERS,
        json={
            "email": "khachhang@fruitstore.com",
            "full_name": "Người khác",
            "password": "Password@123",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_and_me_endpoint(client: AsyncClient) -> None:
    """Đăng nhập bằng tài khoản Manager trả về JWT 30 phút và gọi `/auth/me` thành công."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={
            "email": "manager@fruitstore.com",
            "password": settings.SEED_MANAGER_PASSWORD,
        },
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["expires_in"] == 1800
    assert body["user"]["email"] == "manager@fruitstore.com"
    token = body["access_token"]

    # Gọi /auth/me với Bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={**INTERNAL_HEADERS, "Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "manager@fruitstore.com"


@pytest.mark.asyncio
async def test_google_login_verifies_signature_and_rejects_forged_token(
    client: AsyncClient,
) -> None:
    """
    Kiểm tra lỗi bảo mật #2 đã được sửa:
    - Token Google giả mạo phải bị `google.oauth2.id_token.verify_oauth2_token` từ chối với 401.
    - Token Google hợp lệ (được xác thực chữ ký) tạo tài khoản `CUSTOMER` và trả JWT.
    """
    forged_resp = await client.post(
        "/api/v1/auth/google",
        headers=INTERNAL_HEADERS,
        json={"credential": "eyJhbGciOiJub25lIn0.eyJlbWFpbCI6ImFkbWluQGZydWl0c3RvcmUuY29tIn0."},
    )
    assert forged_resp.status_code == 401
    assert forged_resp.json()["code"] == "INVALID_GOOGLE_TOKEN"

    with patch(
        "app.services.auth_service.google_id_token.verify_oauth2_token"
    ) as mock_verify:
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_CLIENT_ID,
            "email": "googleuser@gmail.com",
            "email_verified": True,
            "name": "Google User",
        }
        valid_resp = await client.post(
            "/api/v1/auth/google",
            headers=INTERNAL_HEADERS,
            json={"credential": "valid.signed.googletoken"},
        )
        assert valid_resp.status_code == 200
        assert valid_resp.json()["user"]["email"] == "googleuser@gmail.com"
        assert [r["code"] for r in valid_resp.json()["user"]["roles"]] == [
            "CUSTOMER"
        ]

