"""
Module: app.services.auth_service
Nhiệm vụ: Xử lý toàn bộ nghiệp vụ xác thực người dùng cho Auth Service:
          - Đăng ký tài khoản khách hàng (`register_user`): luôn gán cố định vai trò `CUSTOMER`.
          - Đăng nhập bằng Email/SĐT + mật khẩu (`authenticate_user`): cấp JWT Access Token 30 phút.
          - Đăng nhập bằng Google OAuth2 (`google_login`): xác thực chữ ký số, `aud`, `iss`, `exp`
            bằng thư viện chính thức `google-auth`.
"""

import secrets
from datetime import datetime, timedelta, timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    GoogleLoginRequest,
    TokenResponse,
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


def build_token_response(user: User) -> TokenResponse:
    """Tạo đối tượng `TokenResponse` chuẩn sau khi xác thực người dùng thành công."""
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
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


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
    session: AsyncSession, payload: UserLogin
) -> TokenResponse:
    """Xác thực đăng nhập bằng Email (hoặc SĐT) và mật khẩu."""
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
    await session.commit()
    await session.refresh(user)

    return build_token_response(user)


async def google_login(
    session: AsyncSession, payload: GoogleLoginRequest
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
        await session.commit()
        user = await repo.get_by_id(user.id)  # type: ignore[assignment]
    else:
        if user.status != "ACTIVE":
            raise AppError(
                status_code=403,
                code="ACCOUNT_LOCKED",
                message=f"Tài khoản đang ở trạng thái '{user.status}'.",
            )
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)

    return build_token_response(user)  # type: ignore[arg-type]

