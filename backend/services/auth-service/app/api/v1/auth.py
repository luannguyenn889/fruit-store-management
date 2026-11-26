"""
Module: app.api.v1.auth
Nhiệm vụ: Định nghĩa các REST API endpoints cho Auth Service (tiền tố `/api/v1/auth`):
          - Xác thực công khai: `POST /register`, `POST /login`, `POST /google`, `POST /refresh`.
          - Phiên & Hồ sơ cá nhân: `POST /logout`, `GET /me`, `PATCH /me`, `POST /change-password`.
          - Quản trị Nhân sự & Phân quyền (ADMIN): `GET /roles`, `GET /users`, `POST /users`,
            `PATCH /users/{id}/roles`, `PATCH /users/{id}/status`.
          Mọi endpoint trong router này đều bắt buộc có header `X-Internal-Key` từ API Gateway.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles, verify_internal_key
from app.core.email import send_password_reset_email
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserRolesUpdate,
    AdminUserStatusUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    InternalUserLookupResponse,
    LogoutRequest,
    MessageResponse,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    RoleResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication, Session & User Management"],
    dependencies=[Depends(verify_internal_key)],
)


def _extract_client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Trích xuất User-Agent và địa chỉ IP của client để lưu vết vào `refresh_tokens`."""
    user_agent = request.headers.get("user-agent")
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )
    return user_agent, ip_address


# =============================================================================
# 1. XÁC THỰC & LÀM MỚI PHIÊN (FR-A01, FR-A02, FR-A03)
# =============================================================================
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản khách hàng mới (Mặc định vai trò CUSTOMER)",
)
async def register(
    payload: UserRegister,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Tạo tài khoản mới với mật khẩu mã hóa Bcrypt và gán vai trò cố định `CUSTOMER`."""
    user = await auth_service.register_user(session, payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập bằng Email/SĐT và mật khẩu (Trả về Access Token 30 phút & Refresh Token)",
)
async def login(
    payload: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Xác thực thông tin đăng nhập và phát hành cặp Access/Refresh Token."""
    user_agent, ip_address = _extract_client_meta(request)
    return await auth_service.authenticate_user(
        session=session,
        payload=payload,
        user_agent=user_agent,
        ip_address=ip_address,
        request_id=request.headers.get("x-request-id"),
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Đăng nhập hoặc đăng ký nhanh bằng Google OAuth2 ID Token",
)
async def login_with_google(
    payload: GoogleLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Kiểm tra chữ ký Google ID Token và trả về cặp Access/Refresh Token của hệ thống."""
    user_agent, ip_address = _extract_client_meta(request)
    return await auth_service.google_login(
        session=session,
        payload=payload,
        user_agent=user_agent,
        ip_address=ip_address,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Gia hạn phiên đăng nhập bằng Refresh Token (Token Rotation - FR-A02)",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Đổi Refresh Token hợp lệ lấy Access Token mới và xoay vòng Refresh Token."""
    user_agent, ip_address = _extract_client_meta(request)
    return await auth_service.refresh_access_token(
        session=session,
        payload=payload,
        user_agent=user_agent,
        ip_address=ip_address,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất và thu hồi Refresh Token ở backend (FR-A03)",
)
async def logout(
    payload: LogoutRequest = LogoutRequest(),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Đánh dấu Refresh Token đã bị thu hồi (`is_revoked = TRUE`)."""
    await auth_service.logout_session(session, current_user, payload)
    return MessageResponse(message="Đã đăng xuất và thu hồi phiên đăng nhập thành công.")


# =============================================================================
# 2. HỒ SƠ CÁ NHÂN & ĐỔI MẬT KHẨU
# =============================================================================
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản và vai trò của người dùng hiện tại",
)
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Trả về thông tin hồ sơ người dùng từ JWT/Gateway Header."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Cập nhật hồ sơ cá nhân (Họ tên, Số điện thoại)",
)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Cho phép người dùng cập nhật họ tên và số điện thoại cá nhân."""
    updated = await auth_service.update_my_profile(session, current_user, payload)
    return UserResponse.model_validate(updated)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Đổi mật khẩu cá nhân và thu hồi các phiên Refresh Token cũ",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Xác minh mật khẩu cũ, cập nhật mật khẩu mới và thu hồi phiên cũ."""
    await auth_service.change_my_password(session, current_user, payload)
    return MessageResponse(
        message="Đã đổi mật khẩu thành công. Các phiên đăng nhập cũ đã được thu hồi."
    )


# =============================================================================
# 3. QUẢN TRỊ NHÂN SỰ & PHÂN QUYỀN (CHỈ ADMIN)
# =============================================================================
@router.get(
    "/roles",
    response_model=List[RoleResponse],
    summary="Lấy danh mục 5 vai trò RBAC (ADMIN, MANAGER)",
)
async def get_roles(
    _: User = Depends(require_roles("ADMIN", "MANAGER")),
    session: AsyncSession = Depends(get_db),
) -> List[RoleResponse]:
    """Trả về danh mục vai trò RBAC của hệ thống."""
    roles = await auth_service.list_roles(session)
    return [RoleResponse.model_validate(r) for r in roles]


@router.get(
    "/users",
    response_model=PaginatedUsersResponse,
    summary="Xem danh sách, tìm kiếm và lọc người dùng/nhân sự (Chỉ ADMIN)",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = Query(default=None, description="Tìm theo họ tên, email hoặc SĐT"),
    role_code: Optional[str] = Query(default=None, description="Lọc theo mã vai trò"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Lọc theo trạng thái ACTIVE/LOCKED/INACTIVE"
    ),
    _: User = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """Tra cứu danh sách toàn bộ tài khoản trong hệ thống."""
    return await auth_service.list_users(
        session=session,
        page=page,
        size=size,
        q=q,
        role_code=role_code,
        status=status_filter,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản nhân viên/quản lý mới (Chỉ ADMIN)",
)
async def create_internal_user(
    payload: AdminUserCreate,
    request: Request,
    actor: User = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Tạo tài khoản mới và gán vai trò nội bộ (`MANAGER`, `STAFF`, `WAREHOUSE`, `ADMIN`)."""
    _, ip_address = _extract_client_meta(request)
    user = await auth_service.admin_create_user(
        session,
        payload,
        actor=actor,
        request_id=request.headers.get("x-request-id"),
        ip_address=ip_address,
    )
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/roles",
    response_model=UserResponse,
    summary="Gán hoặc thay đổi vai trò của một tài khoản (Chỉ ADMIN)",
)
async def update_user_roles(
    user_id: UUID,
    payload: AdminUserRolesUpdate,
    request: Request,
    actor: User = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Cập nhật tập hợp vai trò cho tài khoản chỉ định."""
    _, ip_address = _extract_client_meta(request)
    updated = await auth_service.admin_update_user_roles(
        session=session,
        actor=actor,
        target_user_id=user_id,
        payload=payload,
        request_id=request.headers.get("x-request-id"),
        ip_address=ip_address,
    )
    return UserResponse.model_validate(updated)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Khóa, mở khóa hoặc ngừng hoạt động tài khoản (Chỉ ADMIN)",
)
async def update_user_status(
    user_id: UUID,
    payload: AdminUserStatusUpdate,
    request: Request,
    actor: User = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Thay đổi trạng thái tài khoản (`ACTIVE`, `LOCKED`, `INACTIVE`)."""
    _, ip_address = _extract_client_meta(request)
    updated = await auth_service.admin_update_user_status(
        session=session,
        actor=actor,
        target_user_id=user_id,
        payload=payload,
        request_id=request.headers.get("x-request-id"),
        ip_address=ip_address,
    )
    return UserResponse.model_validate(updated)


# =============================================================================
# 4. QUÊN MẬT KHẨU (FR-A10), AUDIT LOG (FR-H01) & TRA CỨU NỘI BỘ (SPRINT 2)
# =============================================================================
@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Yêu cầu gửi mã xác nhận OTP 6 chữ số đặt lại mật khẩu qua Email (FR-A10)",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Tạo mã OTP 6 chữ số có TTL 15 phút và gửi qua Gmail SMTP ở nền."""
    email_job = await auth_service.request_password_reset(session, payload)
    if email_job is not None:
        to_email, full_name, otp_code = email_job
        background_tasks.add_task(
            send_password_reset_email, to_email, full_name, otp_code
        )
    return MessageResponse(
        message="Nếu email tồn tại trong hệ thống, mã xác nhận 6 chữ số đã được gửi tới hộp thư của bạn."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Đặt lại mật khẩu mới bằng mã OTP 6 chữ số từ Email (FR-A10)",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Kiểm tra mã OTP 6 chữ số còn hiệu lực, cập nhật mật khẩu mới và thu hồi các phiên cũ."""
    _, ip_address = _extract_client_meta(request)
    await auth_service.reset_password_with_token(
        session=session,
        payload=payload,
        request_id=request.headers.get("x-request-id"),
        ip_address=ip_address,
    )
    return MessageResponse(
        message="Đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới."
    )


@router.get(
    "/audit-logs",
    response_model=PaginatedAuditLogsResponse,
    summary="Xem nhật ký Audit Log các thao tác bảo mật/quản trị (Chỉ ADMIN - FR-H01)",
)
async def get_audit_logs(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    action: Optional[str] = Query(default=None),
    target_user_id: Optional[UUID] = Query(default=None),
    _: User = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedAuditLogsResponse:
    """Tra cứu nhật ký bất biến các thao tác phân quyền, khóa tài khoản và đổi mật khẩu."""
    return await auth_service.list_audit_logs(
        session=session,
        page=page,
        size=size,
        action=action,
        target_user_id=target_user_id,
    )


@router.get(
    "/internal/users/{user_id}",
    response_model=InternalUserLookupResponse,
    summary="Tra cứu thông tin user nội bộ giữa các Enterprise Services (Yêu cầu X-Internal-Key)",
)
async def internal_lookup_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> InternalUserLookupResponse:
    """Phục vụ Order/Reporting Service lấy thông tin khách hàng/nhân sự mà không JOIN chéo DB."""
    return await auth_service.get_internal_user_lookup(session, user_id)
