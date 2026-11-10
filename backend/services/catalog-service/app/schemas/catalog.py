"""
Module: app.schemas.catalog
Nhiệm vụ: Định nghĩa các Pydantic v2 DTO cho Catalog Service:
          - Danh mục (`CategoryCreate`, `CategoryUpdate`, `CategoryResponse`).
          - Sản phẩm (`ProductCreate`, `ProductUpdate`, `ProductResponse`, `PaginatedProductsResponse`).
          - Cập nhật đơn giá & Lịch sử giá (`PriceUpdateRequest`, `PriceHistoryResponse`).
          - Tuân thủ NFR-K04: Tiền tệ dùng `Decimal` làm tròn 2 chữ số thập phân và serialize
            ra JSON dưới dạng chuỗi chuẩn (`"65000.00"`).
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, List, Literal, Optional
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
)

# Kiểu dữ liệu枚举 (Literal) đúng theo SRS v1.3
ProductUnitType = Literal["kg", "hop", "qua"]
StorageConditionType = Literal["AMBIENT", "COOL_2_8C", "COOL_8_12C"]
ProductStatusType = Literal["ACTIVE", "INACTIVE", "OUT_OF_SEASON"]


def format_decimal_money(value: Decimal) -> str:
    """Định dạng số tiền Decimal luôn có đúng 2 chữ số thập phân (ví dụ `'65000.00'`)."""
    quantized = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


MoneyDecimal = Annotated[
    Decimal,
    Field(ge=Decimal("0.00"), max_digits=14, decimal_places=2),
    PlainSerializer(format_decimal_money, return_type=str, when_used="json"),
]


# =============================================================================
# 1. SCHEMAS DANH MỤC SẢN PHẨM (CATEGORIES - FR-B03)
# =============================================================================
class CategoryCreate(BaseModel):
    """Schema tạo mới danh mục sản phẩm."""

    name: str = Field(..., min_length=2, max_length=100, description="Tên danh mục trái cây")
    slug: Optional[str] = Field(
        default=None, max_length=120, description="Slug URL (tự sinh từ tên nếu bỏ trống)"
    )
    description: Optional[str] = Field(default=None, description="Mô tả danh mục")
    is_active: bool = Field(default=True, description="Trạng thái kích hoạt")


class CategoryUpdate(BaseModel):
    """Schema cập nhật danh mục sản phẩm."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Schema phản hồi thông tin danh mục sản phẩm."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 2. SCHEMAS SẢN PHẨM TRÁI CÂY (PRODUCTS - FR-B01..B05, FR-B08)
# =============================================================================
class ProductImageResponse(BaseModel):
    """Schema thông tin hình ảnh sản phẩm."""

    id: UUID
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Schema tạo mới sản phẩm trái cây (FR-B04, FR-B08)."""

    category_id: UUID = Field(..., description="ID danh mục sản phẩm")
    sku: str = Field(
        ..., min_length=2, max_length=50, description="Mã SKU duy nhất (VD: XOAI-HL-01)"
    )
    name: str = Field(..., min_length=2, max_length=200, description="Tên sản phẩm trái cây")
    slug: Optional[str] = Field(
        default=None, max_length=220, description="Slug URL (tự sinh nếu bỏ trống)"
    )
    unit: ProductUnitType = Field(
        default="kg", description="Đơn vị tính chuẩn theo SRS: 'kg', 'hop', hoặc 'qua'"
    )
    price: MoneyDecimal = Field(
        ..., description="Đơn giá bán ban đầu (VNĐ, >= 0, ví dụ '65000.00')"
    )
    origin: Optional[str] = Field(
        default=None, max_length=150, description="Xuất xứ (VD: Tiền Giang, Nhập khẩu Úc)"
    )
    default_shelf_life_days: int = Field(
        default=7, gt=0, description="Hạn sử dụng gợi ý tính theo ngày (> 0)"
    )
    storage_condition: StorageConditionType = Field(
        default="COOL_2_8C",
        description="Điều kiện bảo quản: AMBIENT, COOL_2_8C, COOL_8_12C",
    )
    description: Optional[str] = Field(default=None, description="Mô tả chi tiết sản phẩm")
    status: ProductStatusType = Field(
        default="ACTIVE", description="Trạng thái: ACTIVE, INACTIVE, OUT_OF_SEASON"
    )

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Mã SKU không được để trống.")
        return clean


class ProductUpdate(BaseModel):
    """
    Schema cập nhật thông tin sản phẩm (`PATCH /products/{id}`).
    Lưu ý quan trọng (FR-B06 / BR-07): Schema này KHÔNG nhận trường `price`.
    Mọi thay đổi đơn giá bắt buộc phải gọi qua `POST /products/{id}/price` để ghi PriceHistory.
    """

    category_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=220)
    unit: Optional[ProductUnitType] = None
    origin: Optional[str] = Field(default=None, max_length=150)
    default_shelf_life_days: Optional[int] = Field(default=None, gt=0)
    storage_condition: Optional[StorageConditionType] = None
    description: Optional[str] = None
    status: Optional[ProductStatusType] = None

    model_config = ConfigDict(extra="forbid")


class ProductResponse(BaseModel):
    """Schema thông tin chi tiết sản phẩm trả về qua API."""

    id: UUID
    category_id: UUID
    category_name: Optional[str] = None
    sku: str
    name: str
    slug: str
    unit: ProductUnitType
    price: MoneyDecimal
    origin: Optional[str] = None
    default_shelf_life_days: int
    storage_condition: StorageConditionType
    description: Optional[str] = None
    status: ProductStatusType
    images: List[ProductImageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedProductsResponse(BaseModel):
    """Schema phản hồi danh sách sản phẩm có phân trang chuẩn."""

    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# 3. SCHEMAS ĐỔI GIÁ & LỊCH SỬ ĐƠN GIÁ (PRICE HISTORY - FR-B06, BR-07)
# =============================================================================
class PriceUpdateRequest(BaseModel):
    """Schema yêu cầu cập nhật đơn giá sản phẩm kèm lý do (`POST /products/{id}/price`)."""

    new_price: MoneyDecimal = Field(
        ..., description="Đơn giá mới (VNĐ, >= 0, ví dụ '70000.00')"
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Lý do điều chỉnh giá (VD: Giá mùa vụ, Khuyến mãi cuối tuần)",
    )


class PriceHistoryResponse(BaseModel):
    """Schema bản ghi lịch sử thay đổi giá bán của sản phẩm."""

    id: UUID
    product_id: UUID
    old_price: MoneyDecimal
    new_price: MoneyDecimal
    changed_by_user_id: Optional[UUID] = None
    reason: Optional[str] = None
    effective_at: datetime

    model_config = ConfigDict(from_attributes=True)

