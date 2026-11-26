"""
Module: app.schemas.user
Nhiệm vụ: Định nghĩa các Pydantic v2 DTO (Data Transfer Objects) cho Auth Service:
          - Đăng ký công khai (`UserRegister` - không nhận `role_code`), đăng nhập (`UserLogin`, `GoogleLoginRequest`).
          - Phiên làm việc (`TokenResponse`, `RefreshTokenRequest`, `LogoutRequest`).
          - Hồ sơ cá nhân & Đổi mật khẩu (`UpdateProfileRequest`, `ChangePasswordRequest`).
          - Quản trị nhân sự & phân quyền (`AdminUserCreate`, `AdminUserRolesUpdate`,
            `AdminUserStatusUpdate`, `PaginatedUsersResponse`).
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserStatusType = Literal["ACTIVE", "LOCKED", "INACTIVE"]


class RoleResponse(BaseModel):
    """Schema thông tin vai trò trả về trong hồ sơ người dùng và danh mục RBAC."""

    id: int
    code: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    """
    Schema đăng ký tài khoản mới từ phía khách hàng.
    Bảo mật: Không nhận `role_code` từ client; hệ thống luôn gán cố định vai trò `CUSTOMER`.
    """

    email: EmailStr = Field(..., description="Địa chỉ email đăng nhập duy nhất")
    phone: Optional[str] = Field(
        default=None, max_length=20, description="Số điện thoại liên hệ (tùy chọn)"
    )
    full_name: str = Field(
        ..., min_length=2, max_length=150, description="Họ và tên đầy đủ"
    )
    password: str = Field(
        ..., min_length=6, max_length=100, description="Mật khẩu tối thiểu 6 ký tự"
    )


class UserLogin(BaseModel):
    """Schema yêu cầu đăng nhập bằng Email (hoặc SĐT) và mật khẩu."""

    email: str = Field(..., description="Email hoặc số điện thoại đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class GoogleLoginRequest(BaseModel):
    """Schema yêu cầu đăng nhập bằng Google ID Token (Google Identity Services)."""

    credential: str = Field(
        ..., description="Google ID Token (JWT) do Google cấp sau khi xác thực"
    )


class RefreshTokenRequest(BaseModel):
    """Schema yêu cầu cấp lại Access Token bằng Refresh Token (FR-A02)."""

    refresh_token: str = Field(
        ..., min_length=10, description="Refresh Token đang còn hiệu lực"
    )


class LogoutRequest(BaseModel):
    """Schema yêu cầu đăng xuất và thu hồi Refresh Token (FR-A03)."""

    refresh_token: Optional[str] = Field(
        default=None,
        description="Refresh Token cần thu hồi (bỏ trống để thu hồi toàn bộ phiên của tài khoản)",
    )


class UpdateProfileRequest(BaseModel):
    """Schema cập nhật thông tin cá nhân của người dùng đang đăng nhập (`PATCH /auth/me`)."""

    full_name: Optional[str] = Field(
        default=None, min_length=2, max_length=150, description="Họ và tên hiển thị"
    )
    phone: Optional[str] = Field(
        default=None, max_length=20, description="Số điện thoại liên hệ"
    )


class ChangePasswordRequest(BaseModel):
    """Schema đổi mật khẩu cá nhân (`POST /auth/change-password`)."""

    current_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(
        ..., min_length=6, max_length=100, description="Mật khẩu mới tối thiểu 6 ký tự"
    )


class AdminUserCreate(BaseModel):
    """Schema tạo tài khoản nhân sự nội bộ dành riêng cho ADMIN (`POST /auth/users`)."""

    email: EmailStr = Field(..., description="Email đăng nhập duy nhất")
    phone: Optional[str] = Field(default=None, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=6, max_length=100)
    role_codes: List[str] = Field(
        ...,
        min_length=1,
        description="Danh sách mã vai trò (ADMIN, MANAGER, STAFF, WAREHOUSE, CUSTOMER)",
    )


class AdminUserRolesUpdate(BaseModel):
    """Schema cập nhật danh sách vai trò của một tài khoản (`PATCH /auth/users/{id}/roles`)."""

    role_codes: List[str] = Field(
        ..., min_length=1, description="Danh sách mã vai trò mới cần gán"
    )


class AdminUserStatusUpdate(BaseModel):
    """Schema khóa / mở khóa / ngừng hoạt động tài khoản (`PATCH /auth/users/{id}/status`)."""

    status: UserStatusType = Field(
        ..., description="Trạng thái mới: ACTIVE, LOCKED, hoặc INACTIVE"
    )


class UserResponse(BaseModel):
    """Schema thông tin chi tiết người dùng trả về qua API."""

    id: UUID
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    """Schema danh sách người dùng có phân trang cho màn hình Quản trị Nhân sự."""

    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class TokenResponse(BaseModel):
    """Schema phản hồi sau khi đăng nhập hoặc làm mới phiên kèm Access Token & Refresh Token."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(
        ..., description="Thời gian sống của Access Token tính bằng giây"
    )
    user: UserResponse


class MessageResponse(BaseModel):
    """Schema phản hồi thông điệp xác nhận thao tác thành công."""

    message: str


class ForgotPasswordRequest(BaseModel):
    """Schema yêu cầu gửi liên kết đặt lại mật khẩu qua Email (FR-A10)."""

    email: EmailStr = Field(..., description="Email đã đăng ký tài khoản")


class ResetPasswordRequest(BaseModel):
    """Schema đặt lại mật khẩu mới bằng mã OTP 6 chữ số từ Email (FR-A10)."""

    email: EmailStr = Field(..., description="Email tài khoản cần đặt lại mật khẩu")
    otp_code: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="Mã xác nhận OTP gồm đúng 6 chữ số",
    )
    new_password: str = Field(
        ..., min_length=6, max_length=100, description="Mật khẩu mới tối thiểu 6 ký tự"
    )


class AuditLogResponse(BaseModel):
    """Schema một bản ghi nhật ký kiểm toán Auth Service (FR-H01, NFR-S11)."""

    id: UUID
    actor_user_id: Optional[UUID] = None
    target_user_id: Optional[UUID] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLogsResponse(BaseModel):
    """Schema danh sách nhật ký Audit Log có phân trang."""

    items: List[AuditLogResponse]
    total: int
    page: int
    size: int
    pages: int


class InternalUserLookupResponse(BaseModel):
    """Schema tra cứu nhanh thông tin người dùng cho các Enterprise Service nội bộ (Sprint 2)."""

    id: UUID
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    status: str

    model_config = ConfigDict(from_attributes=True)
