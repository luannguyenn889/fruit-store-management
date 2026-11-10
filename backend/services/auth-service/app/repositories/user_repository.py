"""
Module: app.repositories.user_repository
Nhiệm vụ: Thực hiện toàn bộ các truy vấn cơ sở dữ liệu bất đồng bộ (SQLAlchemy 2.0 Async)
          đối với bảng `users` và `roles`. Tách biệt hoàn toàn truy vấn SQL khỏi tầng nghiệp vụ.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Role, User


class UserRepository:
    """Repository quản lý truy vấn dữ liệu người dùng và vai trò trong `fruitstore_auth_db`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Tìm người dùng theo UUID (nạp sẵn danh sách vai trò)."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Tìm người dùng theo địa chỉ email (không phân biệt hoa thường ở tầng chuẩn hóa)."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email.lower().strip())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Tìm người dùng theo số điện thoại."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.phone == phone.strip())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Tìm người dùng theo email hoặc số điện thoại để phục vụ đăng nhập."""
        clean_id = identifier.strip()
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(
                or_(
                    User.email == clean_id.lower(),
                    User.phone == clean_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """Lấy thông tin vai trò theo mã chuẩn (`ADMIN`, `MANAGER`, `STAFF`, `WAREHOUSE`, `CUSTOMER`)."""
        stmt = select(Role).where(Role.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(
        self, code: str, name: str, description: str
    ) -> Role:
        """Tạo mới một vai trò RBAC nếu chưa tồn tại."""
        role = Role(code=code.upper(), name=name, description=description)
        self.session.add(role)
        await self.session.flush()
        return role

    async def create_user(self, user: User) -> User:
        """Thêm người dùng mới vào phiên làm việc hiện tại."""
        self.session.add(user)
        await self.session.flush()
        return user

