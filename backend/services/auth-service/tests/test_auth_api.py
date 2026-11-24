"""
Module: tests.test_auth_api (Auth Service)
Nhiệm vụ: Kiểm thử tự động (Unit & API Tests) toàn diện cho Auth Service:
          1. Kiểm thử Alembic migration `upgrade head -> downgrade -1 -> upgrade head` độc lập (NFR-M02).
          2. Kiểm thử chặn truy cập trực tiếp khi thiếu `X-Internal-Key` (`403 FORBIDDEN_DIRECT_ACCESS`).
          3. Kiểm thử đăng ký công khai (`POST /auth/register`): luôn gán `CUSTOMER`, chặn trùng email (`409`).
          4. Kiểm thử đăng nhập, Refresh Token rotation (`POST /auth/refresh` - FR-A02) và Logout thu hồi phiên
             (`POST /auth/logout` - FR-A03).
          5. Kiểm thử bảo mật Google OAuth2 (`POST /auth/google`).
          6. Kiểm thử cập nhật hồ sơ (`PATCH /auth/me`) & đổi mật khẩu (`POST /auth/change-password`).
          7. Kiểm thử Quản trị Nhân sự & Phân quyền (ADMIN tạo nhân viên, đổi vai trò, khóa tài khoản,
             chặn không phải ADMIN với `403`, chặn ADMIN tự khóa chính mình với `400`).
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
async def test_login_refresh_rotation_and_logout(client: AsyncClient) -> None:
    """Kiểm thử đăng nhập, xoay vòng Refresh Token (FR-A02) và thu hồi phiên khi Logout (FR-A03)."""
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
    assert body["refresh_token"]
    old_refresh = body["refresh_token"]

    # Gọi /auth/refresh -> nhận cặp token mới, refresh token cũ bị vô hiệu hóa
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        headers=INTERNAL_HEADERS,
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh and new_refresh != old_refresh

    # Dùng lại refresh token cũ phải bị chặn 401
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        headers=INTERNAL_HEADERS,
        json={"refresh_token": old_refresh},
    )
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["code"] == "INVALID_REFRESH_TOKEN"

    # Đăng xuất thu hồi refresh token mới -> không dùng refresh lại được nữa
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={**INTERNAL_HEADERS, "Authorization": f"Bearer {new_access}"},
        json={"refresh_token": new_refresh},
    )
    assert logout_resp.status_code == 200

    after_logout_refresh = await client.post(
        "/api/v1/auth/refresh",
        headers=INTERNAL_HEADERS,
        json={"refresh_token": new_refresh},
    )
    assert after_logout_refresh.status_code == 401


@pytest.mark.asyncio
async def test_profile_update_and_change_password(client: AsyncClient) -> None:
    """Kiểm thử cập nhật hồ sơ (`PATCH /auth/me`) và đổi mật khẩu (`POST /auth/change-password`)."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={
            "email": "staff@fruitstore.com",
            "password": settings.SEED_STAFF_PASSWORD,
        },
    )
    token = login_resp.json()["access_token"]
    old_refresh = login_resp.json()["refresh_token"]
    auth_headers = {**INTERNAL_HEADERS, "Authorization": f"Bearer {token}"}

    # Cập nhật họ tên & SĐT
    patch_resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"full_name": "Trần Văn Minh (Ca Sáng)", "phone": "0988777666"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Trần Văn Minh (Ca Sáng)"
    assert patch_resp.json()["phone"] == "0988777666"

    # Sai mật khẩu hiện tại -> 400
    bad_pwd_resp = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "WrongPassword", "new_password": "NewPassword@123"},
    )
    assert bad_pwd_resp.status_code == 400
    assert bad_pwd_resp.json()["code"] == "INVALID_CURRENT_PASSWORD"

    # Đổi mật khẩu thành công -> thu hồi refresh token cũ & đăng nhập được bằng mật khẩu mới
    ok_pwd_resp = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": settings.SEED_STAFF_PASSWORD,
            "new_password": "NewPassword@123",
        },
    )
    assert ok_pwd_resp.status_code == 200

    revoked_check = await client.post(
        "/api/v1/auth/refresh",
        headers=INTERNAL_HEADERS,
        json={"refresh_token": old_refresh},
    )
    assert revoked_check.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={"email": "staff@fruitstore.com", "password": "NewPassword@123"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_admin_user_management_and_rbac(client: AsyncClient) -> None:
    """Kiểm thử Quản trị nhân sự: chặn không phải ADMIN (`403`), ADMIN tạo nhân viên, đổi vai trò và khóa tài khoản."""
    # Manager không có quyền ADMIN truy cập /auth/users -> 403
    mgr_login = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={
            "email": "manager@fruitstore.com",
            "password": settings.SEED_MANAGER_PASSWORD,
        },
    )
    mgr_headers = {
        **INTERNAL_HEADERS,
        "Authorization": f"Bearer {mgr_login.json()['access_token']}",
    }
    forbidden_resp = await client.get("/api/v1/auth/users", headers=mgr_headers)
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["code"] == "FORBIDDEN"

    # Admin đăng nhập
    admin_login = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={
            "email": "admin@fruitstore.com",
            "password": settings.SEED_ADMIN_PASSWORD,
        },
    )
    admin_id = admin_login.json()["user"]["id"]
    admin_headers = {
        **INTERNAL_HEADERS,
        "Authorization": f"Bearer {admin_login.json()['access_token']}",
    }

    # Admin xem danh sách users & roles
    list_resp = await client.get("/api/v1/auth/users", headers=admin_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 4

    # Admin tạo tài khoản thủ kho mới
    create_resp = await client.post(
        "/api/v1/auth/users",
        headers=admin_headers,
        json={
            "email": "kho2@fruitstore.com",
            "phone": "0909123456",
            "full_name": "Phạm Thị Kho",
            "password": "KhoUser@123",
            "role_codes": ["WAREHOUSE"],
        },
    )
    assert create_resp.status_code == 201
    new_user_id = create_resp.json()["id"]
    assert [r["code"] for r in create_resp.json()["roles"]] == ["WAREHOUSE"]

    # Admin đổi vai trò sang STAFF + WAREHOUSE
    role_resp = await client.patch(
        f"/api/v1/auth/users/{new_user_id}/roles",
        headers=admin_headers,
        json={"role_codes": ["STAFF", "WAREHOUSE"]},
    )
    assert role_resp.status_code == 200
    assert sorted(r["code"] for r in role_resp.json()["roles"]) == [
        "STAFF",
        "WAREHOUSE",
    ]

    # Admin không thể tự khóa chính mình -> 400
    self_lock = await client.patch(
        f"/api/v1/auth/users/{admin_id}/status",
        headers=admin_headers,
        json={"status": "LOCKED"},
    )
    assert self_lock.status_code == 400
    assert self_lock.json()["code"] == "CANNOT_LOCK_SELF"

    # Admin khóa tài khoản kho2 -> kho2 đăng nhập bị 403
    lock_resp = await client.patch(
        f"/api/v1/auth/users/{new_user_id}/status",
        headers=admin_headers,
        json={"status": "LOCKED"},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["status"] == "LOCKED"

    locked_login = await client.post(
        "/api/v1/auth/login",
        headers=INTERNAL_HEADERS,
        json={"email": "kho2@fruitstore.com", "password": "KhoUser@123"},
    )
    assert locked_login.status_code == 403


@pytest.mark.asyncio
async def test_google_login_verifies_signature_and_rejects_forged_token(
    client: AsyncClient,
) -> None:
    """
    Kiểm tra bảo mật Google OAuth2:
    - Token Google giả mạo phải bị `verify_oauth2_token` từ chối với 401.
    - Token Google hợp lệ tạo tài khoản `CUSTOMER` và trả cặp Access/Refresh Token.
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
        assert valid_resp.json()["refresh_token"]
        assert [r["code"] for r in valid_resp.json()["user"]["roles"]] == [
            "CUSTOMER"
        ]
