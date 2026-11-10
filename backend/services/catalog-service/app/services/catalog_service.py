"""
Module: app.services.catalog_service
Nhiệm vụ: Xử lý toàn bộ logic nghiệp vụ của Catalog Service (FR-B01..B06, FR-B08, BR-07):
          - Chuẩn hóa đường dẫn thân thiện SEO (`slugify_vietnamese`).
          - Quản lý danh mục trái cây (`Category`): chặn xóa nếu danh mục đang chứa sản phẩm
            với mã lỗi `409 CATEGORY_HAS_PRODUCTS`.
          - Quản lý sản phẩm (`Product`): kiểm tra SKU duy nhất (`409 SKU_ALREADY_EXISTS`),
            tự động ghi bản ghi `PriceHistory` đầu tiên khi tạo sản phẩm mới, cập nhật thông tin
            (không cho đổi giá qua `PATCH`), và ngừng kinh doanh (`POST /deactivate`).
          - Đổi giá nguyên tử (`update_product_price`): sử dụng `SELECT ... FOR UPDATE`, chặn đổi giá
            trùng (`409 PRICE_UNCHANGED`), ghi `PriceHistory` kèm `changed_by_user_id` và `reason`
            trong cùng một transaction duy nhất.
"""

import math
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.exceptions import AppError
from app.models.catalog import Category, PriceHistory, Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    PaginatedProductsResponse,
    PriceUpdateRequest,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


def slugify_vietnamese(text: str) -> str:
    """Chuyển đổi chuỗi tiếng Việt có dấu thành slug URL chuẩn (ví dụ `'Xoài cát Hòa Lộc'` -> `'xoai-cat-hoa-loc'`)."""
    text = text.strip().lower()
    text = text.replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "san-pham"


def quantize_money(value: Decimal) -> Decimal:
    """Chuẩn hóa số tiền Decimal về đúng 2 chữ số thập phân (`NUMERIC(14, 2)`)."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_product_response(product: Product) -> ProductResponse:
    """Chuyển đổi ORM `Product` sang DTO `ProductResponse` kèm `category_name`."""
    resp = ProductResponse.model_validate(product)
    if product.category:
        resp.category_name = product.category.name
    return resp


# =============================================================================
# 1. NGHIỆP VỤ DANH MỤC (CATEGORY SERVICE - FR-B03)
# =============================================================================
async def list_categories(
    session: AsyncSession, is_active: Optional[bool] = None
) -> List[Category]:
    """Lấy danh sách danh mục trái cây."""
    repo = CategoryRepository(session)
    return await repo.list_categories(is_active=is_active)


async def create_category(
    session: AsyncSession, payload: CategoryCreate
) -> Category:
    """Tạo danh mục sản phẩm mới, đảm bảo `slug` không bị trùng."""
    repo = CategoryRepository(session)
    slug = (
        slugify_vietnamese(payload.slug)
        if payload.slug
        else slugify_vietnamese(payload.name)
    )

    existing = await repo.get_by_slug(slug)
    if existing:
        raise AppError(
            status_code=409,
            code="CATEGORY_SLUG_EXISTS",
            message=f"Danh mục với đường dẫn định danh '{slug}' đã tồn tại.",
            details={"slug": slug},
        )

    category = Category(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        is_active=payload.is_active,
    )
    await repo.create(category)
    await session.commit()
    await session.refresh(category)
    return category


async def update_category(
    session: AsyncSession, category_id: UUID, payload: CategoryUpdate
) -> Category:
    """Cập nhật thông tin danh mục sản phẩm."""
    repo = CategoryRepository(session)
    category = await repo.get_by_id(category_id)
    if not category:
        raise AppError(
            status_code=404,
            code="CATEGORY_NOT_FOUND",
            message="Không tìm thấy danh mục sản phẩm.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"]:
        new_slug = slugify_vietnamese(update_data["slug"])
        if new_slug != category.slug:
            conflict = await repo.get_by_slug(new_slug)
            if conflict and conflict.id != category.id:
                raise AppError(
                    status_code=409,
                    code="CATEGORY_SLUG_EXISTS",
                    message=f"Đường dẫn danh mục '{new_slug}' đã được sử dụng.",
                )
            category.slug = new_slug
        update_data.pop("slug", None)

    if "name" in update_data and update_data["name"]:
        category.name = update_data.pop("name").strip()

    for field, value in update_data.items():
        setattr(category, field, value)

    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: UUID) -> None:
    """
    Xóa danh mục sản phẩm (FR-B03).
    Nếu danh mục vẫn còn sản phẩm trực thuộc, chặn xóa và trả về `409 CATEGORY_HAS_PRODUCTS`.
    """
    repo = CategoryRepository(session)
    category = await repo.get_by_id(category_id)
    if not category:
        raise AppError(
            status_code=404,
            code="CATEGORY_NOT_FOUND",
            message="Không tìm thấy danh mục sản phẩm cần xóa.",
        )

    product_count = await repo.count_products(category_id)
    if product_count > 0:
        raise AppError(
            status_code=409,
            code="CATEGORY_HAS_PRODUCTS",
            message=f"Không thể xóa danh mục '{category.name}' vì đang có {product_count} sản phẩm thuộc danh mục này.",
            details={"category_id": str(category_id), "product_count": product_count},
        )

    await repo.delete(category)
    await session.commit()


# =============================================================================
# 2. NGHIỆP VỤ SẢN PHẨM & ĐƠN GIÁ (PRODUCT & PRICE HISTORY SERVICE)
# =============================================================================
async def list_products(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
    q: Optional[str] = None,
    category_id: Optional[UUID] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    status: Optional[str] = None,
) -> PaginatedProductsResponse:
    """Tìm kiếm, lọc và phân trang danh sách sản phẩm (FR-B01)."""
    repo = ProductRepository(session)
    items, total = await repo.list_products(
        page=page,
        size=size,
        q=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        status=status,
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedProductsResponse(
        items=[to_product_response(p) for p in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


async def get_product_detail(
    session: AsyncSession, product_id: UUID
) -> ProductResponse:
    """Lấy thông tin chi tiết một sản phẩm theo ID (FR-B02)."""
    repo = ProductRepository(session)
    product = await repo.get_by_id(product_id)
    if not product:
        raise AppError(
            status_code=404,
            code="PRODUCT_NOT_FOUND",
            message="Không tìm thấy sản phẩm yêu cầu.",
        )
    return to_product_response(product)


async def create_product(
    session: AsyncSession, payload: ProductCreate, actor: Actor
) -> ProductResponse:
    """
    Tạo mới sản phẩm trái cây (FR-B04, FR-B08) và ghi nhận ngay bản ghi lịch sử giá khởi tạo
    (`old_price = new_price = giá ban đầu`) trong cùng một giao dịch.
    """
    cat_repo = CategoryRepository(session)
    prod_repo = ProductRepository(session)

    category = await cat_repo.get_by_id(payload.category_id)
    if not category:
        raise AppError(
            status_code=404,
            code="CATEGORY_NOT_FOUND",
            message="Danh mục sản phẩm được chọn không tồn tại.",
            details={"category_id": str(payload.category_id)},
        )

    clean_sku = payload.sku.strip().upper()
    existing_sku = await prod_repo.get_by_sku(clean_sku)
    if existing_sku:
        raise AppError(
            status_code=409,
            code="SKU_ALREADY_EXISTS",
            message=f"Mã SKU '{clean_sku}' đã tồn tại trong hệ thống. Vui lòng chọn mã SKU khác.",
            details={"sku": clean_sku},
        )

    base_slug = (
        slugify_vietnamese(payload.slug)
        if payload.slug
        else slugify_vietnamese(f"{payload.name}-{clean_sku}")
    )
    existing_slug = await prod_repo.get_by_slug(base_slug)
    if existing_slug:
        raise AppError(
            status_code=409,
            code="PRODUCT_SLUG_EXISTS",
            message=f"Đường dẫn định danh sản phẩm '{base_slug}' đã tồn tại.",
            details={"slug": base_slug},
        )

    initial_price = quantize_money(payload.price)

    product = Product(
        category_id=payload.category_id,
        sku=clean_sku,
        name=payload.name.strip(),
        slug=base_slug,
        unit=payload.unit,
        price=initial_price,
        origin=payload.origin.strip() if payload.origin else None,
        default_shelf_life_days=payload.default_shelf_life_days,
        storage_condition=payload.storage_condition,
        description=payload.description,
        status=payload.status,
    )
    await prod_repo.create_product(product)

    # Ghi luôn bản ghi lịch sử giá đầu tiên khi khởi tạo sản phẩm
    initial_history = PriceHistory(
        product_id=product.id,
        old_price=initial_price,
        new_price=initial_price,
        changed_by_user_id=actor.id,
        reason="Giá khởi tạo khi thêm sản phẩm mới",
    )
    await prod_repo.add_price_history(initial_history)

    await session.commit()
    created = await prod_repo.get_by_id(product.id)
    return to_product_response(created)  # type: ignore[arg-type]


async def update_product(
    session: AsyncSession, product_id: UUID, payload: ProductUpdate
) -> ProductResponse:
    """
    Cập nhật thông tin mô tả, xuất xứ, đơn vị tính, hạn sử dụng gợi ý và điều kiện bảo quản (FR-B04, FR-B08).
    Không cho phép đổi giá tại đây.
    """
    cat_repo = CategoryRepository(session)
    prod_repo = ProductRepository(session)

    product = await prod_repo.get_by_id(product_id)
    if not product:
        raise AppError(
            status_code=404,
            code="PRODUCT_NOT_FOUND",
            message="Không tìm thấy sản phẩm cần cập nhật.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "category_id" in update_data and update_data["category_id"] is not None:
        category = await cat_repo.get_by_id(update_data["category_id"])
        if not category:
            raise AppError(
                status_code=404,
                code="CATEGORY_NOT_FOUND",
                message="Danh mục sản phẩm mới không tồn tại.",
            )

    if "slug" in update_data and update_data["slug"]:
        new_slug = slugify_vietnamese(update_data["slug"])
        if new_slug != product.slug:
            conflict = await prod_repo.get_by_slug(new_slug)
            if conflict and conflict.id != product.id:
                raise AppError(
                    status_code=409,
                    code="PRODUCT_SLUG_EXISTS",
                    message=f"Đường dẫn định danh '{new_slug}' đã được sử dụng.",
                )
            product.slug = new_slug
        update_data.pop("slug", None)

    if "name" in update_data and update_data["name"]:
        product.name = update_data.pop("name").strip()

    for field, value in update_data.items():
        setattr(product, field, value)

    await session.commit()
    updated = await prod_repo.get_by_id(product.id)
    return to_product_response(updated)  # type: ignore[arg-type]


async def deactivate_product(
    session: AsyncSession, product_id: UUID
) -> ProductResponse:
    """
    Ngừng kinh doanh sản phẩm (`status = 'INACTIVE'`) thay vì xóa cứng (FR-B05),
    giúp bảo toàn dữ liệu tham chiếu lịch sử cho Kho và Đơn hàng.
    """
    prod_repo = ProductRepository(session)
    product = await prod_repo.get_by_id(product_id)
    if not product:
        raise AppError(
            status_code=404,
            code="PRODUCT_NOT_FOUND",
            message="Không tìm thấy sản phẩm cần ngừng kinh doanh.",
        )

    product.status = "INACTIVE"
    await session.commit()
    updated = await prod_repo.get_by_id(product.id)
    return to_product_response(updated)  # type: ignore[arg-type]


async def update_product_price(
    session: AsyncSession,
    product_id: UUID,
    payload: PriceUpdateRequest,
    actor: Actor,
) -> ProductResponse:
    """
    Cập nhật đơn giá bán và ghi nhận lịch sử `PriceHistory` nguyên tử (FR-B06, BR-07):
    - Khóa dòng sản phẩm bằng `SELECT ... FOR UPDATE` (`get_for_update`).
    - Nếu giá mới bằng giá hiện hành -> trả lỗi `409 PRICE_UNCHANGED`.
    - Ghi 1 dòng `PriceHistory` (`old_price`, `new_price`, `changed_by_user_id`, `reason`).
    - Cập nhật `product.price = new_price` trong cùng một transaction duy nhất.
    """
    prod_repo = ProductRepository(session)
    new_price = quantize_money(payload.new_price)

    product = await prod_repo.get_for_update(product_id)
    if not product:
        raise AppError(
            status_code=404,
            code="PRODUCT_NOT_FOUND",
            message="Không tìm thấy sản phẩm cần điều chỉnh giá.",
        )

    current_price = quantize_money(product.price)
    if current_price == new_price:
        raise AppError(
            status_code=409,
            code="PRICE_UNCHANGED",
            message="Đơn giá mới trùng với đơn giá hiện tại của sản phẩm.",
            details={
                "current_price": f"{current_price:.2f}",
                "new_price": f"{new_price:.2f}",
            },
        )

    history = PriceHistory(
        product_id=product.id,
        old_price=current_price,
        new_price=new_price,
        changed_by_user_id=actor.id,
        reason=(
            payload.reason.strip()
            if payload.reason and payload.reason.strip()
            else "Điều chỉnh giá bán"
        ),
    )
    await prod_repo.add_price_history(history)
    product.price = new_price

    await session.commit()
    updated = await prod_repo.get_by_id(product.id)
    return to_product_response(updated)  # type: ignore[arg-type]


async def get_product_price_history(
    session: AsyncSession, product_id: UUID
) -> List[PriceHistory]:
    """Lấy danh sách lịch sử thay đổi giá bán của sản phẩm (FR-B06)."""
    prod_repo = ProductRepository(session)
    product = await prod_repo.get_by_id(product_id)
    if not product:
        raise AppError(
            status_code=404,
            code="PRODUCT_NOT_FOUND",
            message="Không tìm thấy sản phẩm cần tra cứu lịch sử giá.",
        )
    return await prod_repo.list_price_history(product_id)

