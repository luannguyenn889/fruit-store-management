"""
Module: app.repositories.product_repository
Nhiệm vụ: Thực hiện toàn bộ truy vấn SQLAlchemy 2.0 Async đối với bảng `products`
          và `price_history` trong `fruitstore_catalog_db`:
          - Tìm kiếm, lọc đa tiêu chí và phân trang sản phẩm (`FR-B01`).
          - Kiểm tra trùng lặp `sku` và `slug` (`FR-B04`).
          - Khóa dòng dữ liệu bằng `SELECT ... FOR UPDATE` (`get_for_update`) để đảm bảo
            tính nguyên tử khi cập nhật đơn giá đồng thời (`FR-B06`, `BR-07`).
          - Ghi mới và truy vấn lịch sử thay đổi giá (`PriceHistory`).
"""

from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import PriceHistory, Product


class ProductRepository:
    """Repository quản lý truy vấn dữ liệu bảng `products` và `price_history`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        """Lấy thông tin chi tiết sản phẩm theo UUID (kèm danh mục và hình ảnh)."""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
            )
            .where(Product.id == product_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_update(self, product_id: UUID) -> Optional[Product]:
        """
        Truy vấn sản phẩm kèm khóa bi quan `SELECT ... FOR UPDATE`.
        Đảm bảo hai yêu cầu đổi giá đồng thời được tuần tự hóa, không làm mất dòng `PriceHistory`.
        """
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
            )
            .where(Product.id == product_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Tìm sản phẩm theo mã SKU duy nhất (chuẩn hóa chữ in hoa)."""
        stmt = select(Product).where(Product.sku == sku.strip().upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Product]:
        """Tìm sản phẩm theo slug URL."""
        stmt = select(Product).where(Product.slug == slug.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_products(
        self,
        page: int = 1,
        size: int = 20,
        q: Optional[str] = None,
        category_id: Optional[UUID] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Product], int]:
        """
        Tìm kiếm, lọc và phân trang danh sách sản phẩm trái cây (FR-B01):
        - `q`: Tìm theo tên sản phẩm, mã SKU hoặc nguồn gốc xuất xứ.
        - `category_id`: Lọc theo danh mục.
        - `min_price`, `max_price`: Lọc theo khoảng giá bán.
        - `status`: Lọc theo trạng thái (`ACTIVE`, `INACTIVE`, `OUT_OF_SEASON`).
        """
        filters = []
        if q and q.strip():
            keyword = f"%{q.strip()}%"
            filters.append(
                or_(
                    Product.name.ilike(keyword),
                    Product.sku.ilike(keyword),
                    Product.origin.ilike(keyword),
                )
            )
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if status and status.strip():
            filters.append(Product.status == status.strip().upper())

        count_stmt = select(func.count()).select_from(Product)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar_one() or 0)

        offset = (page - 1) * size
        data_stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
            )
            .order_by(Product.created_at.desc(), Product.name.asc())
            .offset(offset)
            .limit(size)
        )
        if filters:
            data_stmt = data_stmt.where(*filters)

        result = await self.session.execute(data_stmt)
        items = list(result.scalars().all())
        return items, total

    async def create_product(self, product: Product) -> Product:
        """Thêm sản phẩm mới vào phiên làm việc hiện tại."""
        self.session.add(product)
        await self.session.flush()
        return product

    async def add_price_history(self, history: PriceHistory) -> PriceHistory:
        """Thêm một bản ghi bất biến vào bảng `price_history`."""
        self.session.add(history)
        await self.session.flush()
        return history

    async def list_price_history(
        self, product_id: UUID
    ) -> List[PriceHistory]:
        """Lấy toàn bộ lịch sử thay đổi giá của một sản phẩm theo thứ tự mới nhất trước."""
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.effective_at.desc(), PriceHistory.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

