"""
Module: app.repositories.user_repository
Nhiệm vụ: Thực hiện toàn bộ các truy vấn cơ sở dữ liệu bất đồng bộ (SQLAlchemy 2.0 Async)
          đối với các bảng `users`, `roles`, `user_roles` và `refresh_tokens`.
          Tách biệt hoàn toàn truy vấn SQL khỏi tầng nghiệp vụ.
"""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import RefreshToken, Role, User


class UserRepository:
    """Repository quản lý truy vấn dữ liệu người dùng, vai trò và phiên Refresh Token."""

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
        """Tìm người dùng theo địa chỉ email."""
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

    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
        q: Optional[str] = None,
        role_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """
        Tìm kiếm, lọc và phân trang danh sách người dùng cho màn hình Quản trị Nhân sự.
        Hỗ trợ lọc theo từ khóa (họ tên, email, SĐT), mã vai trò và trạng thái tài khoản.
        """
        filters = []
        if q and q.strip():
            keyword = f"%{q.strip()}%"
            filters.append(
                or_(
                    User.full_name.ilike(keyword),
                    User.email.ilike(keyword),
                    User.phone.ilike(keyword),
                )
            )
        if status and status.strip():
            filters.append(User.status == status.strip().upper())
        if role_code and role_code.strip():
            filters.append(User.roles.any(Role.code == role_code.strip().upper()))

        count_stmt = select(func.count()).select_from(User)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)

        offset = (page - 1) * size
        data_stmt = (
            select(User)
            .options(selectinload(User.roles))
            .order_by(User.created_at.desc(), User.email.asc())
            .offset(offset)
            .limit(size)
        )
        if filters:
            data_stmt = data_stmt.where(*filters)

        result = await self.session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def list_roles(self) -> List[Role]:
        """Lấy toàn bộ danh mục vai trò RBAC trong hệ thống."""
        stmt = select(Role).order_by(Role.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """Lấy thông tin vai trò theo mã chuẩn (`ADMIN`, `MANAGER`, `STAFF`, `WAREHOUSE`, `CUSTOMER`)."""
        stmt = select(Role).where(Role.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_roles_by_codes(self, codes: List[str]) -> List[Role]:
        """Lấy danh sách các vai trò theo tập hợp mã vai trò."""
        normalized = [c.strip().upper() for c in codes if c.strip()]
        if not normalized:
            return []
        stmt = select(Role).where(Role.code.in_(normalized))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    # =========================================================================
    # TRUY VẤN BẢNG REFRESH_TOKENS (FR-A02, FR-A03)
    # =========================================================================
    async def create_refresh_token(
        self, refresh_token: RefreshToken
    ) -> RefreshToken:
        """Lưu bản ghi Refresh Token (đã băm SHA-256) vào bảng `refresh_tokens`."""
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> Optional[RefreshToken]:
        """Tra cứu Refresh Token theo mã băm SHA-256."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        """Thu hồi toàn bộ Refresh Token đang hoạt động của một người dùng (khi đổi mật khẩu hoặc bị khóa)."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)
