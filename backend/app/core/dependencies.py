import uuid
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database.sessions import get_auth_db
from app.models.user import User
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_auth_db),
) -> User:
    """Dependency trích xuất và xác thực người dùng từ Bearer JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Thông tin xác thực không hợp lệ hoặc token đã hết hạn.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = AuthService.get_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản người dùng đã bị vô hiệu hóa.",
        )

    return user


def require_roles(allowed_roles: List[str]):
    """Dependency kiểm tra vai trò người dùng (RBAC)"""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = [r.code for r in current_user.roles]
        # Admin luôn có toàn quyền
        if "ADMIN" in user_roles:
            return current_user

        has_permission = any(role in allowed_roles for role in user_roles)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền thực hiện thao tác này. Quyền yêu cầu: {allowed_roles}",
            )
        return current_user

    return role_checker

