"""
Module: app.schemas.user
Nhiệm vụ: Định nghĩa các Pydantic v2 DTO (Data Transfer Objects) cho Auth Service:
          - `UserRegister`: Dữ liệu đăng ký tài khoản công khai (KHÔNG cho phép truyền `role_code`
            để ngăn chặn lỗ hổng tự nâng quyền).
          - `UserLogin`, `GoogleLoginRequest`: Dữ liệu đăng nhập.
          - `UserResponse`, `TokenResponse`: Dữ liệu trả về cho Client/Gateway.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleResponse(BaseModel):
    """Schema thông tin vai trò trả về trong hồ sơ người dùng."""

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


class TokenResponse(BaseModel):
    """Schema phản hồi sau khi đăng nhập thành công kèm JWT Access Token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ..., description="Thời gian sống của Access Token tính bằng giây"
    )
    user: UserResponse

