"""
Module: app.schemas.procurement (Inventory Service)
Nhiệm vụ: Định nghĩa các Pydantic v2 DTO (Request / Response) cho phân hệ
          Nhà cung cấp (`suppliers`) và Phiếu nhập kho (`purchase_orders`,
          `purchase_items`) của Thành viên 2 (FR-C01, FR-C02, FR-C03, NFR-K04).
          Tuân thủ NFR-K04: Sử dụng `Decimal` cho toàn bộ trường tiền tệ
          (`NUMERIC(14, 2)`) và khối lượng/số lượng (`NUMERIC(10, 3)`),
          tuyệt đối không dùng `float`.
"""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

SUPPLIER_CODE_PATTERN = re.compile(r"^NCC-[A-Z0-9][A-Z0-9_-]*$")


# =============================================================================
# 1. SCHEMAS NHÀ CUNG CẤP (SUPPLIERS - FR-C01)
# =============================================================================
class SupplierCreate(BaseModel):
    """Dữ liệu đầu vào khi tạo mới nhà cung cấp (FR-C01)."""

    code: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=50,
        description="Mã nhà cung cấp duy nhất dạng NCC-001 (tự sinh nếu bỏ trống).",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Tên nhà cung cấp.",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Số điện thoại liên hệ.",
    )
    address: Optional[str] = Field(
        default=None,
        description="Địa chỉ nhà cung cấp.",
    )
    is_active: bool = Field(
        default=True,
        description="Trạng thái đang hợp tác hay tạm ngừng.",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: Optional[str]) -> Optional[str]:
        """Chuẩn hóa và kiểm tra mã nhà cung cấp phải bắt đầu bằng `NCC-`."""
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not SUPPLIER_CODE_PATTERN.match(cleaned):
            raise ValueError(
                "Mã nhà cung cấp phải đúng định dạng NCC-xxx (ví dụ: NCC-001)."
            )
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Loại bỏ khoảng trắng thừa và chặn tên nhà cung cấp rỗng."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tên nhà cung cấp không được để trống.")
        return cleaned

    @field_validator("phone", "address")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Chuẩn hóa chuỗi tùy chọn: chuỗi chỉ có khoảng trắng sẽ thành None."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SupplierUpdate(BaseModel):
    """Dữ liệu đầu vào khi cập nhật thông tin nhà cung cấp (PATCH)."""

    code: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=50,
        description="Mã nhà cung cấp mới (nếu đổi), phải duy nhất dạng NCC-xxx.",
    )
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Tên nhà cung cấp mới.",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Số điện thoại mới.",
    )
    address: Optional[str] = Field(
        default=None,
        description="Địa chỉ mới.",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Bật/tắt trạng thái hoạt động của nhà cung cấp.",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: Optional[str]) -> Optional[str]:
        """Kiểm tra định dạng `NCC-xxx` khi người dùng cập nhật mã."""
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not SUPPLIER_CODE_PATTERN.match(cleaned):
            raise ValueError(
                "Mã nhà cung cấp phải đúng định dạng NCC-xxx (ví dụ: NCC-001)."
            )
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """Chặn cập nhật tên thành chuỗi rỗng."""
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tên nhà cung cấp không được để trống.")
        return cleaned

    @field_validator("phone", "address")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Chuẩn hóa chuỗi tùy chọn."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SupplierResponse(BaseModel):
    """Thông tin chi tiết một nhà cung cấp trả về qua API."""

    id: UUID
    code: str
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    """Danh sách nhà cung cấp có phân trang."""

    items: List[SupplierResponse]
    total: int
    page: int
    limit: int
    pages: int


# =============================================================================
# 2. SCHEMAS PHIẾU NHẬP KHO & DÒNG CHI TIẾT (PURCHASE ORDERS - FR-C02)
# =============================================================================
class PurchaseItemCreate(BaseModel):
    """Một dòng sản phẩm trong yêu cầu lập phiếu nhập kho (FR-C02)."""

    product_id: UUID = Field(
        ...,
        description="UUID sản phẩm (tham chiếu logic tới Catalog Service).",
    )
    quantity_ordered: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=10,
        decimal_places=3,
        description="Số lượng đặt nhập (NUMERIC(10, 3), hỗ trợ cân lẻ kg).",
    )
    unit_cost: Decimal = Field(
        ...,
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        description="Đơn giá vốn nhập kho VNĐ (NUMERIC(14, 2)).",
    )
    expected_expiry_date: Optional[date] = Field(
        default=None,
        validation_alias=AliasChoices("expected_expiry_date", "expiry_date"),
        description="Hạn sử dụng dự kiến của lô hàng.",
    )

    model_config = ConfigDict(populate_by_name=True)


class PurchaseOrderCreate(BaseModel):
    """Dữ liệu đầu vào khi lập phiếu nhập kho mới (trạng thái khởi tạo DRAFT)."""

    supplier_id: UUID = Field(..., description="UUID nhà cung cấp.")
    items: List[PurchaseItemCreate] = Field(
        ...,
        min_length=1,
        description="Danh sách các dòng sản phẩm nhập kho (ít nhất 1 dòng).",
    )


class PurchaseItemResponse(BaseModel):
    """Thông tin chi tiết một dòng sản phẩm trên phiếu nhập kho."""

    id: UUID
    purchase_order_id: UUID
    product_id: UUID
    quantity_ordered: Decimal = Field(..., max_digits=10, decimal_places=3)
    quantity_received: Decimal = Field(..., max_digits=10, decimal_places=3)
    unit_cost: Decimal = Field(..., max_digits=14, decimal_places=2)
    line_total: Decimal = Field(..., max_digits=14, decimal_places=2)
    expected_expiry_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    """Thông tin phiếu nhập kho kèm danh sách dòng chi tiết."""

    id: UUID
    po_number: str
    supplier_id: UUID
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    status: str
    total_amount: Decimal = Field(..., max_digits=14, decimal_places=2)
    created_by_user_id: UUID
    received_at: Optional[datetime] = None
    created_at: datetime
    items: List[PurchaseItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderListResponse(BaseModel):
    """Danh sách phiếu nhập kho có phân trang."""

    items: List[PurchaseOrderResponse]
    total: int
    page: int
    limit: int
    pages: int


# =============================================================================
# 3. SCHEMAS XÁC NHẬN NHẬP KHO & SINH LÔ (RECEIVE PO - FR-C03, BR-03, AC-01)
# =============================================================================
class PurchaseItemReceiveInput(BaseModel):
    """Tùy chọn ghi đè số lượng thực nhận / hạn sử dụng khi xác nhận nhập kho."""

    purchase_item_id: Optional[UUID] = Field(
        default=None,
        description="UUID dòng phiếu nhập cần ghi đè (ưu tiên khớp theo ID dòng).",
    )
    product_id: Optional[UUID] = Field(
        default=None,
        description="UUID sản phẩm để khớp dòng nếu không truyền purchase_item_id.",
    )
    quantity_received: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0"),
        max_digits=10,
        decimal_places=3,
        description="Số lượng thực nhận (mặc định bằng quantity_ordered).",
    )
    expiry_date: Optional[date] = Field(
        default=None,
        description="Hạn sử dụng thực tế của lô hàng (mặc định lấy expected_expiry_date).",
    )
    lot_code: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=60,
        description="Mã lô tùy chỉnh (tự sinh nếu bỏ trống).",
    )

    @field_validator("lot_code")
    @classmethod
    def normalize_lot_code(cls, value: Optional[str]) -> Optional[str]:
        """Chuẩn hóa mã lô tùy chỉnh."""
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Mã lô hàng không được để trống.")
        return cleaned


class PurchaseOrderReceiveRequest(BaseModel):
    """Dữ liệu tùy chọn khi gọi `POST /purchase-orders/{id}/receive`."""

    received_date: Optional[date] = Field(
        default=None,
        description="Ngày nhập kho thực tế của các lô hàng (mặc định là hôm nay).",
    )
    items: Optional[List[PurchaseItemReceiveInput]] = Field(
        default=None,
        description="Thông tin thực nhận theo từng dòng (bỏ trống để nhận đủ theo phiếu).",
    )


class CreatedStockLotSummary(BaseModel):
    """Tóm tắt lô hàng `stock_lots` vừa được sinh khi xác nhận nhập kho."""

    id: UUID
    lot_code: str
    product_id: UUID
    supplier_id: UUID
    purchase_order_id: UUID
    quantity_received: Decimal = Field(..., max_digits=10, decimal_places=3)
    quantity_remaining: Decimal = Field(..., max_digits=10, decimal_places=3)
    quantity_reserved: Decimal = Field(..., max_digits=10, decimal_places=3)
    unit_cost: Decimal = Field(..., max_digits=14, decimal_places=2)
    received_date: date
    expiry_date: date
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreatedStockMovementSummary(BaseModel):
    """Tóm tắt bản ghi sổ cái `stock_movements` loại `IN` vừa được ghi nhận."""

    id: UUID
    lot_id: UUID
    movement_type: str
    quantity_change: Decimal = Field(..., max_digits=10, decimal_places=3)
    unit_cost_snapshot: Decimal = Field(..., max_digits=14, decimal_places=2)
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    reason: Optional[str] = None
    performed_by_user_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderReceiveResponse(BaseModel):
    """Kết quả xác nhận nhập kho nguyên tử (FR-C03, AC-01)."""

    purchase_order: PurchaseOrderResponse
    created_lots: List[CreatedStockLotSummary]
    created_movements: List[CreatedStockMovementSummary]
