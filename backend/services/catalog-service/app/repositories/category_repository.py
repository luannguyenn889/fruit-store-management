"""
Module: app.repositories.category_repository
Nhiệm vụ: Thực hiện các truy vấn cơ sở dữ liệu bất đồng bộ (SQLAlchemy 2.0 Async)
          đối với bảng `categories` trong `fruitstore_catalog_db`, bao gồm kiểm tra
          trùng lặp slug và đếm số lượng sản phẩm thuộc danh mục trước khi xóa (FR-B03).
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category, Product


class CategoryRepository:
    """Repository quản lý truy vấn dữ liệu bảng `categories`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(
        self, is_active: Optional[bool] = None
    ) -> List[Category]:
        """Lấy danh sách danh mục sản phẩm (tùy chọn lọc theo `is_active`)."""
        stmt = select(Category).order_by(Category.name.asc())
        if is_active is not None:
            stmt = stmt.where(Category.is_active == is_active)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, category_id: UUID) -> Optional[Category]:
        """Tìm danh mục theo UUID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Tìm danh mục theo đường dẫn slug duy nhất."""
        stmt = select(Category).where(Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_products(self, category_id: UUID) -> int:
        """Đếm số lượng sản phẩm đang tham chiếu tới danh mục này (phục vụ kiểm tra trước khi xóa)."""
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def create(self, category: Category) -> Category:
        """Thêm mới một danh mục sản phẩm vào phiên làm việc."""
        self.session.add(category)
        await self.session.flush()
        return category

    async def delete(self, category: Category) -> None:
        """Xóa một danh mục sản phẩm khỏi phiên làm việc."""
        await self.session.delete(category)
        await self.session.flush()

