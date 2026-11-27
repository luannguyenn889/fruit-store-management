"""
Module: app.core.deps (Chatbot Service)
Nhiệm vụ: Xác thực `X-Internal-Key` từ API Gateway và trích xuất ngữ cảnh người dùng (`Actor`),
          hỗ trợ cả khách vãng lai (`GUEST`) khi chat công khai trên `/shop` và người dùng đã đăng nhập.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from fastapi import Header

from app.core.config import settings
from app.core.exceptions import AppError


@dataclass(frozen=True)
class ChatActor:
    """Thông tin người dùng gửi tin nhắn tới Chatbot Service."""

    user_id: Optional[UUID]
    role: str


async def verify_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> None:
    """Từ chối mọi request không đi qua API Gateway."""
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise AppError(
            status_code=403,
            code="FORBIDDEN_DIRECT_ACCESS",
            message="Truy cập trực tiếp vào Chatbot Service bị từ chối. Vui lòng gọi qua API Gateway.",
        )


async def get_optional_actor(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
) -> ChatActor:
    """Trích xuất người dùng đã đăng nhập hoặc trả về `GUEST` nếu là khách vãng lai."""
    if not x_user_id:
        return ChatActor(user_id=None, role="GUEST")
    try:
        parsed_id = UUID(x_user_id)
    except ValueError as exc:
        raise AppError(
            status_code=401,
            code="INVALID_USER_ID",
            message="Định danh người dùng (X-User-Id) không hợp lệ.",
        ) from exc
    role = (x_user_role or "CUSTOMER").upper().strip()
    return ChatActor(user_id=parsed_id, role=role)


async def get_authenticated_actor(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
) -> ChatActor:
    """Yêu cầu người dùng đã đăng nhập để xem/xóa lịch sử phiên chat cá nhân."""
    actor = await get_optional_actor(x_user_id=x_user_id, x_user_role=x_user_role)
    if actor.user_id is None:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Vui lòng đăng nhập để quản lý lịch sử hội thoại.",
        )
    return actor
