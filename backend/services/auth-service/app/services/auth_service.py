"""
Module: app.services.auth_service
Nhiệm vụ: Xử lý toàn bộ nghiệp vụ xác thực, quản lý phiên và quản trị nhân sự cho Auth Service:
          1. Đăng ký công khai (`register_user`): luôn gán cố định vai trò `CUSTOMER`.
          2. Đăng nhập Email/SĐT + mật khẩu (`authenticate_user`) & Google OAuth2 (`google_login`):
             phát hành Access Token (30 phút) kèm Refresh Token (7 ngày lưu SHA-256 trong `refresh_tokens`).
          3. Làm mới phiên (`refresh_access_token` - FR-A02) với cơ chế xoay vòng Refresh Token (rotation)
             và Đăng xuất thu hồi phiên (`logout_session` - FR-A03).
          4. Hồ sơ cá nhân (`update_my_profile`) & Đổi mật khẩu (`change_my_password`).
          5. Quản trị nhân sự & phân quyền dành cho ADMIN (`list_users`, `list_roles`,
             `admin_create_user`, `admin_update_user_roles`, `admin_update_user_status`).
"""

import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    AdminUserCreate,
    AdminUserRolesUpdate,
    AdminUserStatusUpdate,
    ChangePasswordRequest,
    GoogleLoginRequest,
    LogoutRequest,
    PaginatedUsersResponse,
    RefreshTokenRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)

# Thứ tự ưu tiên vai trò khi chọn role chính đưa vào claim `role` của JWT
ROLE_PRIORITY = ["ADMIN", "MANAGER", "STAFF", "WAREHOUSE", "CUSTOMER"]


def resolve_primary_role(user: User) -> str:
    """Xác định vai trò có độ ưu tiên cao nhất của người dùng để gắn vào JWT claim `role`."""
    user_role_codes = {r.code.upper() for r in user.roles}
    for code in ROLE_PRIORITY:
        if code in user_role_codes:
            return code
    return "CUSTOMER"


def build_token_response(
    user: User, raw_refresh_token: Optional[str] = None
) -> TokenResponse:
    """Tạo đối tượng `TokenResponse` chuẩn sau khi xác thực hoặc làm mới phiên thành công."""
    primary_role = resolve_primary_role(user)
    role_codes = [r.code for r in user.roles] or [primary_role]
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        subject=str(user.id),
        role=primary_role,
        extra_claims={
            "email": user.email,
            "roles": role_codes,
        },
        expires_delta=expires_delta,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


async def issue_session_tokens(
    session: AsyncSession,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """
    Sinh cặp Access Token (30 phút) và Refresh Token (7 ngày), lưu mã băm SHA-256
    của Refresh Token vào bảng `refresh_tokens` (FR-A02).
    """
    repo = UserRepository(session)
    raw_refresh = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=(ip_address or "")[:64] or None,
        is_revoked=False,
        expires_at=expires_at,
    )
    await repo.create_refresh_token(rt_record)
    await session.commit()
    return build_token_response(user, raw_refresh_token=raw_refresh)


async def register_user(
    session: AsyncSession, payload: UserRegister
) -> User:
    """
    Đăng ký tài khoản mới từ phía công khai.
    Bảo mật (FR-A01): Không nhận `role_code` từ client, luôn gán vai trò `CUSTOMER`.
    """
    repo = UserRepository(session)
    normalized_email = payload.email.lower().strip()

    existing_email = await repo.get_by_email(normalized_email)
    if existing_email:
        raise AppError(
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
            message="Địa chỉ email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập.",
        )

    clean_phone = payload.phone.strip() if payload.phone else None
    if clean_phone:
        existing_phone = await repo.get_by_phone(clean_phone)
        if existing_phone:
            raise AppError(
                status_code=409,
                code="PHONE_ALREADY_EXISTS",
                message="Số điện thoại này đã được sử dụng cho một tài khoản khác.",
            )

    customer_role = await repo.get_role_by_code("CUSTOMER")
    if not customer_role:
        customer_role = await repo.create_role(
            code="CUSTOMER",
            name="Khách hàng",
            description="Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng",
        )

    new_user = User(
        email=normalized_email,
        phone=clean_phone,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        status="ACTIVE",
        roles=[customer_role],
    )
    await repo.create_user(new_user)
    await session.commit()
    return await repo.get_by_id(new_user.id)  # type: ignore[return-value]


async def authenticate_user(
    session: AsyncSession,
    payload: UserLogin,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """Xác thực đăng nhập bằng Email (hoặc SĐT) + mật khẩu và phát hành cặp Access/Refresh Token."""
    repo = UserRepository(session)
    user = await repo.get_by_identifier(payload.email)

    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Email/số điện thoại hoặc mật khẩu không chính xác.",
        )

    if user.status != "ACTIVE":
        raise AppError(
            status_code=403,
            code="ACCOUNT_LOCKED",
            message=f"Tài khoản của bạn hiện đang ở trạng thái '{user.status}'. Vui lòng liên hệ quản trị viên.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    return await issue_session_tokens(
        session=session,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )


async def google_login(
    session: AsyncSession,
    payload: GoogleLoginRequest,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """
    Xác thực đăng nhập bằng Google ID Token.
    Bảo mật: Sử dụng `google.oauth2.id_token.verify_oauth2_token` để kiểm tra chữ ký RSA của Google,
    đối chiếu `aud` với `GOOGLE_CLIENT_ID`, kiểm tra `iss` và thời hạn `exp`.
    """
    try:
        id_info = google_id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as exc:
        raise AppError(
            status_code=401,
            code="INVALID_GOOGLE_TOKEN",
            message="Xác thực Google không hợp lệ hoặc phiên đã hết hạn.",
            details={"reason": str(exc)},
        ) from exc

    issuer = id_info.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise AppError(
            status_code=401,
            code="INVALID_GOOGLE_ISSUER",
            message="Nguồn phát hành Google Token không hợp lệ.",
        )

    email = (id_info.get("email") or "").lower().strip()
    if not email or not id_info.get("email_verified", False):
        raise AppError(
            status_code=401,
            code="UNVERIFIED_GOOGLE_EMAIL",
            message="Tài khoản Google chưa xác minh địa chỉ email.",
        )

    full_name = (id_info.get("name") or email.split("@")[0]).strip()

    repo = UserRepository(session)
    user = await repo.get_by_email(email)

    if not user:
        customer_role = await repo.get_role_by_code("CUSTOMER")
        if not customer_role:
            customer_role = await repo.create_role(
                code="CUSTOMER",
                name="Khách hàng",
                description="Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng",
            )
        user = User(
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            full_name=full_name,
            status="ACTIVE",
            last_login_at=datetime.now(timezone.utc),
            roles=[customer_role],
        )
        await repo.create_user(user)
        await session.flush()
        user = await repo.get_by_id(user.id)  # type: ignore[assignment]
    else:
        if user.status != "ACTIVE":
            raise AppError(
                status_code=403,
                code="ACCOUNT_LOCKED",
                message=f"Tài khoản đang ở trạng thái '{user.status}'.",
            )
        user.last_login_at = datetime.now(timezone.utc)

    return await issue_session_tokens(
        session=session,
        user=user,  # type: ignore[arg-type]
        user_agent=user_agent,
        ip_address=ip_address,
    )


async def refresh_access_token(
    session: AsyncSession,
    payload: RefreshTokenRequest,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """
    Gia hạn phiên đăng nhập bằng Refresh Token (FR-A02).
    Áp dụng cơ chế Token Rotation: thu hồi Refresh Token cũ và phát hành cặp token mới.
    """
    repo = UserRepository(session)
    token_digest = hash_token(payload.refresh_token.strip())
    stored_token = await repo.get_refresh_token_by_hash(token_digest)

    if not stored_token or stored_token.is_revoked:
        raise AppError(
            status_code=401,
            code="INVALID_REFRESH_TOKEN",
            message="Phiên làm mới không hợp lệ hoặc đã bị thu hồi. Vui lòng đăng nhập lại.",
        )

    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        stored_token.is_revoked = True
        await session.commit()
        raise AppError(
            status_code=401,
            code="REFRESH_TOKEN_EXPIRED",
            message="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )

    user = await repo.get_by_id(stored_token.user_id)
    if not user or user.status != "ACTIVE":
        stored_token.is_revoked = True
        await session.commit()
        raise AppError(
            status_code=403,
            code="ACCOUNT_INACTIVE",
            message="Tài khoản không còn hoạt động hoặc đã bị khóa.",
        )

    # Thu hồi Refresh Token cũ và cấp cặp Access + Refresh Token mới
    stored_token.is_revoked = True
    return await issue_session_tokens(
        session=session,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )


async def logout_session(
    session: AsyncSession,
    current_user: User,
    payload: LogoutRequest,
) -> None:
    """
    Đăng xuất và thu hồi Refresh Token ở backend (FR-A03).
    Nếu truyền `refresh_token`, chỉ thu hồi phiên đó; nếu bỏ trống, thu hồi toàn bộ phiên của tài khoản.
    """
    repo = UserRepository(session)
    if payload.refresh_token and payload.refresh_token.strip():
        stored = await repo.get_refresh_token_by_hash(
            hash_token(payload.refresh_token.strip())
        )
        if stored and stored.user_id == current_user.id:
            stored.is_revoked = True
    else:
        await repo.revoke_all_user_refresh_tokens(current_user.id)

    await session.commit()


# =============================================================================
# HỒ SƠ CÁ NHÂN & ĐỔI MẬT KHẨU (SELF-SERVICE)
# =============================================================================
async def update_my_profile(
    session: AsyncSession,
    current_user: User,
    payload: UpdateProfileRequest,
) -> User:
    """Cập nhật họ tên và số điện thoại cho tài khoản đang đăng nhập (`PATCH /auth/me`)."""
    repo = UserRepository(session)

    if payload.full_name is not None:
        clean_name = payload.full_name.strip()
        if len(clean_name) < 2:
            raise AppError(
                status_code=422,
                code="INVALID_FULL_NAME",
                message="Họ và tên phải có tối thiểu 2 ký tự.",
            )
        current_user.full_name = clean_name

    if payload.phone is not None:
        clean_phone = payload.phone.strip() or None
        if clean_phone and clean_phone != current_user.phone:
            existing_phone = await repo.get_by_phone(clean_phone)
            if existing_phone and existing_phone.id != current_user.id:
                raise AppError(
                    status_code=409,
                    code="PHONE_ALREADY_EXISTS",
                    message="Số điện thoại này đã được sử dụng bởi tài khoản khác.",
                )
        current_user.phone = clean_phone

    await session.commit()
    return await repo.get_by_id(current_user.id)  # type: ignore[return-value]


async def change_my_password(
    session: AsyncSession,
    current_user: User,
    payload: ChangePasswordRequest,
) -> None:
    """
    Đổi mật khẩu cho người dùng hiện tại (`POST /auth/change-password`).
    Thu hồi toàn bộ Refresh Token cũ để bảo vệ an toàn phiên đăng nhập.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise AppError(
            status_code=400,
            code="INVALID_CURRENT_PASSWORD",
            message="Mật khẩu hiện tại không chính xác.",
        )

    if payload.current_password == payload.new_password:
        raise AppError(
            status_code=400,
            code="SAME_PASSWORD",
            message="Mật khẩu mới phải khác mật khẩu hiện tại.",
        )

    repo = UserRepository(session)
    current_user.password_hash = get_password_hash(payload.new_password)
    await repo.revoke_all_user_refresh_tokens(current_user.id)
    await session.commit()


# =============================================================================
# QUẢN TRỊ NHÂN SỰ & PHÂN QUYỀN (CHỈ ADMIN)
# =============================================================================
async def list_roles(session: AsyncSession) -> List[Role]:
    """Trả về toàn bộ danh sách vai trò RBAC của hệ thống."""
    repo = UserRepository(session)
    return await repo.list_roles()


async def list_users(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
    q: Optional[str] = None,
    role_code: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedUsersResponse:
    """Tra cứu, lọc và phân trang danh sách nhân sự/người dùng cho màn hình Quản trị."""
    repo = UserRepository(session)
    users, total = await repo.list_users(
        page=page, size=size, q=q, role_code=role_code, status=status
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


async def admin_create_user(
    session: AsyncSession, payload: AdminUserCreate
) -> User:
    """Tạo tài khoản nội bộ mới kèm danh sách vai trò được chỉ định (chỉ dành cho ADMIN)."""
    repo = UserRepository(session)
    normalized_email = payload.email.lower().strip()

    if await repo.get_by_email(normalized_email):
        raise AppError(
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
            message=f"Email '{normalized_email}' đã tồn tại trong hệ thống.",
        )

    clean_phone = payload.phone.strip() if payload.phone else None
    if clean_phone and await repo.get_by_phone(clean_phone):
        raise AppError(
            status_code=409,
            code="PHONE_ALREADY_EXISTS",
            message=f"Số điện thoại '{clean_phone}' đã được đăng ký.",
        )

    requested_codes = sorted({c.strip().upper() for c in payload.role_codes if c.strip()})
    roles = await repo.get_roles_by_codes(requested_codes)
    found_codes = {r.code.upper() for r in roles}
    missing = [c for c in requested_codes if c not in found_codes]
    if missing:
        raise AppError(
            status_code=400,
            code="INVALID_ROLE_CODE",
            message=f"Mã vai trò không hợp lệ: {', '.join(missing)}.",
            details={"invalid_roles": missing},
        )

    new_user = User(
        email=normalized_email,
        phone=clean_phone,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        status="ACTIVE",
        roles=roles,
    )
    await repo.create_user(new_user)
    await session.commit()
    return await repo.get_by_id(new_user.id)  # type: ignore[return-value]


async def admin_update_user_roles(
    session: AsyncSession,
    actor: User,
    target_user_id: UUID,
    payload: AdminUserRolesUpdate,
) -> User:
    """Cập nhật vai trò cho một tài khoản (chặn ADMIN tự tước quyền ADMIN của chính mình)."""
    repo = UserRepository(session)
    target_user = await repo.get_by_id(target_user_id)
    if not target_user:
        raise AppError(
            status_code=404,
            code="USER_NOT_FOUND",
            message="Không tìm thấy tài khoản cần cập nhật vai trò.",
        )

    requested_codes = sorted({c.strip().upper() for c in payload.role_codes if c.strip()})
    if target_user.id == actor.id and "ADMIN" not in requested_codes:
        raise AppError(
            status_code=400,
            code="CANNOT_REMOVE_OWN_ADMIN_ROLE",
            message="Bạn không thể tự gỡ bỏ vai trò Quản trị viên (ADMIN) của chính mình.",
        )

    roles = await repo.get_roles_by_codes(requested_codes)
    found_codes = {r.code.upper() for r in roles}
    missing = [c for c in requested_codes if c not in found_codes]
    if missing:
        raise AppError(
            status_code=400,
            code="INVALID_ROLE_CODE",
            message=f"Mã vai trò không hợp lệ: {', '.join(missing)}.",
            details={"invalid_roles": missing},
        )

    target_user.roles = roles
    await session.commit()
    return await repo.get_by_id(target_user.id)  # type: ignore[return-value]


async def admin_update_user_status(
    session: AsyncSession,
    actor: User,
    target_user_id: UUID,
    payload: AdminUserStatusUpdate,
) -> User:
    """
    Khóa / mở khóa / ngừng kích hoạt tài khoản (chỉ dành cho ADMIN).
    Chặn ADMIN tự khóa chính mình và tự động thu hồi toàn bộ Refresh Token nếu tài khoản bị khóa.
    """
    repo = UserRepository(session)
    target_user = await repo.get_by_id(target_user_id)
    if not target_user:
        raise AppError(
            status_code=404,
            code="USER_NOT_FOUND",
            message="Không tìm thấy tài khoản cần thay đổi trạng thái.",
        )

    if target_user.id == actor.id and payload.status != "ACTIVE":
        raise AppError(
            status_code=400,
            code="CANNOT_LOCK_SELF",
            message="Bạn không thể tự khóa hoặc vô hiệu hóa tài khoản đang đăng nhập của chính mình.",
        )

    target_user.status = payload.status
    if payload.status != "ACTIVE":
        await repo.revoke_all_user_refresh_tokens(target_user.id)

    await session.commit()
    return await repo.get_by_id(target_user.id)  # type: ignore[return-value]
