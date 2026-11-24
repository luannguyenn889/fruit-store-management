from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LotResponse(BaseModel):
    id: UUID
    lot_code: str
    product_id: UUID
    supplier_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    quantity_received: Decimal = Field(..., max_digits=10, decimal_places=3)
    quantity_remaining: Decimal = Field(..., max_digits=10, decimal_places=3)
    quantity_reserved: Decimal = Field(..., max_digits=10, decimal_places=3)
    available_quantity: Decimal = Field(..., max_digits=10, decimal_places=3)
    unit_cost: Decimal = Field(..., max_digits=14, decimal_places=2)
    received_date: date
    expiry_date: date
    status: str
    days_until_expiry: int
    is_expired: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LotListResponse(BaseModel):
    items: List[LotResponse]
    total: int
    page: int
    limit: int
    pages: int


class ProductStockSummary(BaseModel):
    product_id: UUID
    total_received: Decimal = Field(..., max_digits=10, decimal_places=3)
    total_remaining: Decimal = Field(..., max_digits=10, decimal_places=3)
    total_reserved: Decimal = Field(..., max_digits=10, decimal_places=3)
    available_quantity: Decimal = Field(..., max_digits=10, decimal_places=3)
    active_lots_count: int
    near_expiry_lots_count: int
    expired_lots_count: int


class StockSummaryResponse(BaseModel):
    total_products: int
    total_available_quantity: Decimal = Field(..., max_digits=12, decimal_places=3)
    total_reserved_quantity: Decimal = Field(..., max_digits=12, decimal_places=3)
    total_remaining_quantity: Decimal = Field(..., max_digits=12, decimal_places=3)
    products: List[ProductStockSummary]


class ExpiringLotsResponse(BaseModel):
    days_threshold: int
    total_near_expiry: int
    total_expired: int
    near_expiry_lots: List[LotResponse]
    expired_lots: List[LotResponse]


class ReservationItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0, max_digits=10, decimal_places=3)


class ReservationCreateRequest(BaseModel):
    order_id: UUID
    idempotency_key: Optional[str] = Field(default=None, max_length=100)
    items: List[ReservationItemCreate] = Field(..., min_length=1)


class ReservationItemResponse(BaseModel):
    id: UUID
    reservation_id: UUID
    lot_id: UUID
    lot_code: str
    product_id: UUID
    quantity: Decimal = Field(..., max_digits=10, decimal_places=3)
    expiry_date: date

    model_config = ConfigDict(from_attributes=True)


class ReservationResponse(BaseModel):
    id: UUID
    order_id: UUID
    idempotency_key: str
    status: str
    expires_at: datetime
    created_at: datetime
    items: List[ReservationItemResponse]

    model_config = ConfigDict(from_attributes=True)


class ExpireOverdueResponse(BaseModel):
    expired_count: int
    expired_reservation_ids: List[UUID]
    message: str


class WastageCreateRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0, max_digits=10, decimal_places=3)
    reason_type: Literal["WASTE_EXPIRED", "WASTE_DAMAGED"]
    note: str = Field(..., min_length=1)


class AdjustmentCreateRequest(BaseModel):
    actual_quantity: Decimal = Field(..., ge=0, max_digits=10, decimal_places=3)
    reason: str = Field(..., min_length=1)


class StockMovementResponse(BaseModel):
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


class StockMovementListResponse(BaseModel):
    items: List[StockMovementResponse]
    total: int
    page: int
    limit: int
    pages: int
