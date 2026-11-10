"""
Module: app.api.v1.catalog
Nhiệm vụ: Định nghĩa các REST API endpoints cho Catalog Service (tiền tố `/api/v1/catalog`):
          - Danh mục (`GET /categories`, `POST /categories`, `PATCH /categories/{id}`, `DELETE /categories/{id}`).
          - Sản phẩm (`GET /products`, `GET /products/{id}`, `POST /products`, `PATCH /products/{id}`,
            `POST /products/{id}/deactivate`).
          - Đơn giá & Lịch sử giá (`POST /products/{id}/price`, `GET /products/{id}/price-history`).
          Tất cả thao tác ghi đều kiểm tra quyền `MANAGER` hoặc `ADMIN` tại backend (NFR-S03).
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor, require_roles, verify_internal_key
from app.db.session import get_db
from app.schemas.catalog import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    PaginatedProductsResponse,
    PriceHistoryResponse,
    PriceUpdateRequest,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services import catalog_service

router = APIRouter(
    prefix="/catalog",
    tags=["Catalog - Categories, Products & Price History"],
    dependencies=[Depends(verify_internal_key)],
)


# =============================================================================
# 1. ENDPOINTS DANH MỤC SẢN PHẨM (CATEGORIES - FR-B03)
# =============================================================================
@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Lấy danh sách danh mục trái cây (Công khai)",
)
async def get_categories(
    is_active: Optional[bool] = Query(
        default=None, description="Lọc theo trạng thái kích hoạt"
    ),
    session: AsyncSession = Depends(get_db),
) -> List[CategoryResponse]:
    """Trả về danh sách danh mục sản phẩm trái cây."""
    categories = await catalog_service.list_categories(session, is_active=is_active)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo danh mục trái cây mới (Chỉ Manager, Admin)",
)
async def create_category(
    payload: CategoryCreate,
    session: AsyncSession = Depends(get_db),
    _: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> CategoryResponse:
    """Tạo mới một danh mục sản phẩm."""
    category = await catalog_service.create_category(session, payload)
    return CategoryResponse.model_validate(category)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Cập nhật danh mục trái cây (Chỉ Manager, Admin)",
)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    session: AsyncSession = Depends(get_db),
    _: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> CategoryResponse:
    """Cập nhật thông tin danh mục theo ID."""
    category = await catalog_service.update_category(session, category_id, payload)
    return CategoryResponse.model_validate(category)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa danh mục trái cây nếu chưa có sản phẩm (Chỉ Manager, Admin)",
)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> Response:
    """Xóa danh mục; trả về `409 CATEGORY_HAS_PRODUCTS` nếu danh mục vẫn còn sản phẩm."""
    await catalog_service.delete_category(session, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 2. ENDPOINTS SẢN PHẨM TRÁI CÂY (PRODUCTS - FR-B01..B05, FR-B08)
# =============================================================================
@router.get(
    "/products",
    response_model=PaginatedProductsResponse,
    summary="Tìm kiếm, lọc và phân trang danh sách sản phẩm trái cây (Công khai)",
)
async def get_products(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    size: int = Query(
        default=20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"
    ),
    q: Optional[str] = Query(
        default=None, description="Từ khóa tìm kiếm theo tên, SKU hoặc xuất xứ"
    ),
    category_id: Optional[UUID] = Query(
        default=None, description="Lọc theo UUID danh mục"
    ),
    min_price: Optional[Decimal] = Query(
        default=None, ge=0, description="Giá tối thiểu"
    ),
    max_price: Optional[Decimal] = Query(
        default=None, ge=0, description="Giá tối đa"
    ),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Lọc theo trạng thái: ACTIVE, INACTIVE, OUT_OF_SEASON",
    ),
    session: AsyncSession = Depends(get_db),
) -> PaginatedProductsResponse:
    """Tra cứu danh sách sản phẩm trái cây có hỗ trợ lọc và phân trang."""
    return await catalog_service.list_products(
        session=session,
        page=page,
        size=size,
        q=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        status=status_filter,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Xem chi tiết một sản phẩm trái cây (Công khai)",
)
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Lấy thông tin chi tiết sản phẩm theo UUID."""
    return await catalog_service.get_product_detail(session, product_id)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm sản phẩm trái cây mới với SKU duy nhất (Chỉ Manager, Admin)",
)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_db),
    actor: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> ProductResponse:
    """Tạo sản phẩm mới và lưu bản ghi lịch sử giá khởi tạo."""
    return await catalog_service.create_product(session, payload, actor)


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Cập nhật thông tin sản phẩm - không bao gồm đơn giá (Chỉ Manager, Admin)",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    session: AsyncSession = Depends(get_db),
    _: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> ProductResponse:
    """Cập nhật tên, mô tả, xuất xứ, đơn vị tính, hạn dùng gợi ý hoặc điều kiện bảo quản."""
    return await catalog_service.update_product(session, product_id, payload)


@router.post(
    "/products/{product_id}/deactivate",
    response_model=ProductResponse,
    summary="Ngừng kinh doanh sản phẩm -> INACTIVE (Chỉ Manager, Admin)",
)
async def deactivate_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> ProductResponse:
    """Chuyển trạng thái sản phẩm sang `INACTIVE` để bảo toàn tham chiếu lịch sử."""
    return await catalog_service.deactivate_product(session, product_id)


# =============================================================================
# 3. ENDPOINTS CẬP NHẬT ĐƠN GIÁ & LỊCH SỬ GIÁ (PRICE HISTORY - FR-B06, BR-07)
# =============================================================================
@router.post(
    "/products/{product_id}/price",
    response_model=ProductResponse,
    summary="Cập nhật đơn giá bán và ghi nhận PriceHistory nguyên tử (Chỉ Manager, Admin)",
)
async def change_product_price(
    product_id: UUID,
    payload: PriceUpdateRequest,
    session: AsyncSession = Depends(get_db),
    actor: Actor = Depends(require_roles("MANAGER", "ADMIN")),
) -> ProductResponse:
    """
    Đổi đơn giá sản phẩm trong một giao dịch có khóa `SELECT ... FOR UPDATE`
    và lưu vết vào bảng bất biến `price_history`.
    """
    return await catalog_service.update_product_price(
        session=session,
        product_id=product_id,
        payload=payload,
        actor=actor,
    )


@router.get(
    "/products/{product_id}/price-history",
    response_model=List[PriceHistoryResponse],
    summary="Xem lịch sử thay đổi đơn giá của sản phẩm (Công khai)",
)
async def get_price_history(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> List[PriceHistoryResponse]:
    """Lấy danh sách lịch sử biến động giá bán của một sản phẩm."""
    records = await catalog_service.get_product_price_history(session, product_id)
    return [PriceHistoryResponse.model_validate(r) for r in records]

