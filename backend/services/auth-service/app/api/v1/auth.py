"""
Module: app.api.v1.auth
Nhiệm vụ: Định nghĩa các REST API endpoints cho Auth Service (tiền tố `/api/v1/auth`):
          - `POST /register`: Đăng ký tài khoản khách hàng (`CUSTOMER`).
          - `POST /login`: Đăng nhập bằng Email/SĐT + mật khẩu, trả về JWT (30 phút).
          - `POST /google`: Đăng nhập bằng Google OAuth2 đã xác thực chữ ký.
          - `GET /me`: Lấy thông tin hồ sơ người dùng đang đăng nhập.
          Mọi endpoint trong router này đều bắt buộc có header `X-Internal-Key` từ API Gateway.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_internal_key
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    GoogleLoginRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & RBAC"],
    dependencies=[Depends(verify_internal_key)],
)


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
    summary="Đăng nhập bằng Email/SĐT và mật khẩu (Trả về JWT Access Token 30 phút)",
)
async def login(
    payload: UserLogin,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Xác thực thông tin đăng nhập và phát hành JWT Access Token."""
    return await auth_service.authenticate_user(session, payload)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Đăng nhập hoặc đăng ký nhanh bằng Google OAuth2 ID Token",
)
async def login_with_google(
    payload: GoogleLoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Kiểm tra chữ ký Google ID Token và trả về JWT Access Token của hệ thống."""
    return await auth_service.google_login(session, payload)


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

