"""
Module: app.core.deps
Nhiệm vụ: Cung cấp các FastAPI Dependencies dùng cho Auth Service:
          - Kiểm tra header `X-Internal-Key` để đảm bảo request đi qua API Gateway.
          - Trích xuất người dùng hiện tại từ header `X-User-Id` (do Gateway gắn)
            hoặc từ `Authorization: Bearer <token>` để phục vụ endpoint `/auth/me`.
"""

from typing import Optional
from uuid import UUID
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def verify_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> None:
    """
    Xác thực khóa nội bộ từ API Gateway.
    Ngăn chặn việc client bên ngoài gọi trực tiếp vào cổng nội bộ 8001 của Auth Service.
    """
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise AppError(
            status_code=403,
            code="FORBIDDEN_DIRECT_ACCESS",
            message="Truy cập trực tiếp vào service nội bộ bị từ chối. Vui lòng gọi qua API Gateway.",
        )


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """
    Lấy thông tin người dùng đang đăng nhập cho endpoint `/auth/me`.
    Ưu tiên đọc `X-User-Id` đã được API Gateway xác thực; hỗ trợ fallback đọc từ Bearer JWT.
    """
    resolved_user_id: Optional[UUID] = None

    if x_user_id:
        try:
            resolved_user_id = UUID(x_user_id)
        except ValueError as exc:
            raise AppError(
                status_code=401,
                code="INVALID_USER_HEADER",
                message="Định danh người dùng trong header không hợp lệ.",
            ) from exc
    elif credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if not payload or not payload.get("sub"):
            raise AppError(
                status_code=401,
                code="INVALID_TOKEN",
                message="Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.",
            )
        try:
            resolved_user_id = UUID(str(payload["sub"]))
        except ValueError as exc:
            raise AppError(
                status_code=401,
                code="INVALID_TOKEN_SUBJECT",
                message="Thông tin định danh trong token không hợp lệ.",
            ) from exc
    else:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Vui lòng đăng nhập để thực hiện thao tác này.",
        )

    repo = UserRepository(session)
    user = await repo.get_by_id(resolved_user_id)
    if not user:
        raise AppError(
            status_code=401,
            code="USER_NOT_FOUND",
            message="Tài khoản người dùng không tồn tại trong hệ thống.",
        )

    if user.status != "ACTIVE":
        raise AppError(
            status_code=403,
            code="ACCOUNT_INACTIVE",
            message=f"Tài khoản hiện đang ở trạng thái '{user.status}', không thể truy cập.",
        )

    return user

