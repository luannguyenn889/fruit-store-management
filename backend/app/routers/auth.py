from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.core.security import create_access_token
from app.database.sessions import get_auth_db
from app.models.user import User, Role
from app.schemas.user import (
    UserRegister,
    UserLogin,
    GoogleLoginRequest,
    UserResponse,
    TokenResponse,
    RoleResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])


def _user_to_response(user: User) -> UserResponse:
    """Helper chuyển đổi User model sang UserResponse schema"""
    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        status=user.status,
        roles=[r.code for r in user.roles],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản người dùng mới",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_auth_db),
):
    """
    Tạo tài khoản người dùng mới:
    - **email**: Địa chỉ email duy nhất
    - **password**: Mật khẩu ít nhất 6 ký tự
    - **full_name**: Họ và tên
    - **phone**: Số điện thoại (tùy chọn)
    - **role_code**: Mặc định là 'CUSTOMER'
    """
    user = AuthService.register(db, user_in)
    return _user_to_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập tài khoản & nhận JWT Access Token (JSON body)",
)
def login(
    login_in: UserLogin,
    db: Session = Depends(get_auth_db),
):
    """
    Đăng nhập bằng Email và Mật khẩu:
    - Trả về Bearer JWT token có hạn 120 phút
    """
    user = AuthService.authenticate(db, login_in.email, login_in.password)
    primary_role = user.roles[0].code if user.roles else "CUSTOMER"
    token = create_access_token(subject=user.id, role=primary_role)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_response(user),
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Đăng nhập / Đăng ký nhanh bằng Google OAuth (Google Identity Services)",
)
def login_with_google(
    google_in: GoogleLoginRequest,
    db: Session = Depends(get_auth_db),
):
    """
    Xác thực Google ID token nhận từ Client:
    - Nếu đã có tài khoản: đăng nhập và trả về JWT
    - Nếu chưa có tài khoản: tự động tạo tài khoản mới với vai trò CUSTOMER và trả về JWT
    """
    user = AuthService.authenticate_google(db, google_in.credential)
    primary_role = user.roles[0].code if user.roles else "CUSTOMER"
    token = create_access_token(subject=user.id, role=primary_role)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_response(user),
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=False,
    summary="Endpoint tương thích Swagger UI OAuth2 authorize button",
)
def login_swagger_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_auth_db),
):
    """Dành riêng cho nút 'Authorize' trên Swagger UI"""
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    primary_role = user.roles[0].code if user.roles else "CUSTOMER"
    token = create_access_token(subject=user.id, role=primary_role)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_response(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản người dùng hiện tại",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Xác thực token JWT gửi qua Header `Authorization: Bearer <token>`
    và trả về thông tin cá nhân cùng các vai trò được phân quyền.
    """
    return _user_to_response(current_user)


@router.get(
    "/roles",
    response_model=List[RoleResponse],
    summary="Xem danh sách tất cả các vai trò trong hệ thống (Chỉ Admin)",
)
def list_roles(
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_auth_db),
):
    """Danh sách các Role hệ thống (ADMIN, MANAGER, STAFF, WAREHOUSE_STAFF, CUSTOMER)"""
    roles = db.query(Role).all()
    return roles

