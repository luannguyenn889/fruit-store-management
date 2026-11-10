"""
Module: app.core.deps (Catalog Service)
Nhiệm vụ: Cung cấp các dependencies kiểm soát truy cập và phân quyền (RBAC) tại backend
          cho Catalog Service (NFR-S03):
          - `verify_internal_key`: Từ chối mọi request không đi qua API Gateway (`X-Internal-Key`).
          - `require_roles(*allowed)`: Đọc `X-User-Id` và `X-User-Role` từ header do Gateway gắn,
            kiểm tra vai trò được phép (ví dụ `MANAGER`, `ADMIN`) và trả về đối tượng `Actor`.
"""

from dataclasses import dataclass
from typing import Callable, Optional
from uuid import UUID
from fastapi import Header

from app.core.config import settings
from app.core.exceptions import AppError


@dataclass(frozen=True)
class Actor:
    """Thông tin định danh và vai trò của người thực hiện thao tác (trích từ header Gateway)."""

    id: UUID
    role: str


async def verify_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> None:
    """
    Đảm bảo request được chuyển tiếp hợp lệ từ API Gateway.
    Nếu thiếu hoặc sai `X-Internal-Key`, từ chối ngay với mã 403 `FORBIDDEN_DIRECT_ACCESS`.
    """
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise AppError(
            status_code=403,
            code="FORBIDDEN_DIRECT_ACCESS",
            message="Truy cập trực tiếp vào Catalog Service bị từ chối. Vui lòng gọi qua API Gateway.",
        )


def require_roles(*allowed_roles: str) -> Callable[..., Actor]:
    """
    Dependency factory kiểm tra phân quyền RBAC ở tầng service (NFR-S03).
    Chỉ cho phép người dùng có vai trò nằm trong `allowed_roles` hoặc `ADMIN`.
    """
    normalized_allowed = {r.upper() for r in allowed_roles}

    async def dependency(
        x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
        x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    ) -> Actor:
        if not x_user_id or not x_user_role:
            raise AppError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Vui lòng đăng nhập để thực hiện thao tác này.",
            )

        try:
            actor_uuid = UUID(x_user_id)
        except ValueError as exc:
            raise AppError(
                status_code=401,
                code="INVALID_USER_ID",
                message="Định danh người dùng (X-User-Id) không hợp lệ.",
            ) from exc

        role_upper = x_user_role.upper().strip()
        if role_upper not in normalized_allowed and role_upper != "ADMIN":
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền thực hiện thao tác này. Yêu cầu quyền Quản lý (MANAGER) hoặc Quản trị viên (ADMIN).",
                details={"required_roles": sorted(normalized_allowed), "current_role": role_upper},
            )

        return Actor(id=actor_uuid, role=role_upper)

    return dependency

