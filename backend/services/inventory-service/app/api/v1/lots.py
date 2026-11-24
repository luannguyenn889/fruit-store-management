from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor, require_roles, verify_internal_key
from app.db.session import get_db
from app.schemas.lot import (
    AdjustmentCreateRequest,
    ExpireOverdueResponse,
    ExpiringLotsResponse,
    LotListResponse,
    LotResponse,
    ReservationCreateRequest,
    ReservationResponse,
    StockMovementListResponse,
    StockSummaryResponse,
    WastageCreateRequest,
)
from app.services.lot_service import LotService

require_inventory_read = require_roles('WAREHOUSE', 'MANAGER', 'STAFF', 'ADMIN')
require_inventory_write = require_roles('WAREHOUSE', 'MANAGER', 'ADMIN')

router = APIRouter(prefix='/inventory', dependencies=[Depends(verify_internal_key)])


@router.get(
    "/stock/summary",
    response_model=StockSummaryResponse,
    tags=["Stock Summary"],
    summary="Tong hop ton kho",
)
async def get_stock_summary(
    product_id: Optional[UUID] = Query(default=None),
    _: Actor = Depends(require_inventory_read),
    session: AsyncSession = Depends(get_db),
) -> StockSummaryResponse:
    service = LotService(session)
    return await service.get_stock_summary(product_id=product_id)


@router.get(
    "/lots/expiring",
    response_model=ExpiringLotsResponse,
    tags=["Lots"],
    summary="Danh sach lo sap het han va qua han",
)
async def get_expiring_lots(
    days: int = Query(default=3, ge=1, le=30),
    _: Actor = Depends(require_inventory_read),
    session: AsyncSession = Depends(get_db),
) -> ExpiringLotsResponse:
    service = LotService(session)
    return await service.get_expiring_lots(days=days)


@router.get(
    "/lots",
    response_model=LotListResponse,
    tags=["Lots"],
    summary="Danh sach lo hang",
)
async def list_lots(
    product_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: Actor = Depends(require_inventory_read),
    session: AsyncSession = Depends(get_db),
) -> LotListResponse:
    service = LotService(session)
    return await service.list_lots(
        product_id=product_id, status=status, page=page, limit=limit
    )


@router.get(
    "/lots/{lot_id}",
    response_model=LotResponse,
    tags=["Lots"],
    summary="Chi tiet lo hang",
)
async def get_lot_by_id(
    lot_id: UUID,
    _: Actor = Depends(require_inventory_read),
    session: AsyncSession = Depends(get_db),
) -> LotResponse:
    service = LotService(session)
    return await service.get_lot_by_id(lot_id=lot_id)


@router.post(
    "/lots/{lot_id}/wastage",
    response_model=LotResponse,
    tags=["Wastage"],
    summary="Ghi nhan hao hut lo hang",
)
async def record_wastage(
    lot_id: UUID,
    request_data: WastageCreateRequest,
    actor: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> LotResponse:
    service = LotService(session)
    return await service.record_wastage(lot_id=lot_id, req=request_data, actor=actor)


@router.post(
    "/lots/{lot_id}/adjust",
    response_model=LotResponse,
    tags=["Wastage"],
    summary="Dieu chinh ton kho kiem ke",
)
async def adjust_stock(
    lot_id: UUID,
    request_data: AdjustmentCreateRequest,
    actor: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> LotResponse:
    service = LotService(session)
    return await service.adjust_stock(lot_id=lot_id, req=request_data, actor=actor)


@router.get(
    "/movements",
    response_model=StockMovementListResponse,
    tags=["Movements"],
    summary="Nhat ky bien dong kho",
)
async def list_movements(
    product_id: Optional[UUID] = Query(default=None),
    lot_id: Optional[UUID] = Query(default=None),
    movement_type: Optional[str] = Query(default=None),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: Actor = Depends(require_inventory_read),
    session: AsyncSession = Depends(get_db),
) -> StockMovementListResponse:
    service = LotService(session)
    return await service.list_movements(
        product_id=product_id,
        lot_id=lot_id,
        movement_type=movement_type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )


@router.post(
    "/reservations/expire-overdue",
    response_model=ExpireOverdueResponse,
    tags=["Reservations"],
    summary="Don dep phieu giu hang qua han",
)
async def expire_overdue_reservations(
    _: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> ExpireOverdueResponse:
    service = LotService(session)
    return await service.expire_overdue_reservations()


@router.post(
    "/reservations",
    response_model=ReservationResponse,
    tags=["Reservations"],
    summary="Tao phieu giu hang theo FEFO",
)
async def create_reservation(
    request_data: ReservationCreateRequest,
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    actor: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    key = idempotency_key_header or request_data.idempotency_key
    if not key:
        from app.core.exceptions import AppError
        raise AppError(
            status_code=400,
            code="MISSING_IDEMPOTENCY_KEY",
            message="Yeu cau header Idempotency-Key hoac truong idempotency_key trong body.",
        )
    request_data.idempotency_key = key

    service = LotService(session)
    return await service.create_reservation(req=request_data, actor=actor)


@router.post(
    "/reservations/{reservation_id}/commit",
    response_model=ReservationResponse,
    tags=["Reservations"],
    summary="Xac nhan xuat kho don giu hang",
)
async def commit_reservation(
    reservation_id: UUID,
    actor: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    service = LotService(session)
    return await service.commit_reservation(reservation_id=reservation_id, actor=actor)


@router.post(
    "/reservations/{reservation_id}/release",
    response_model=ReservationResponse,
    tags=["Reservations"],
    summary="Giai phong phieu giu hang",
)
async def release_reservation(
    reservation_id: UUID,
    actor: Actor = Depends(require_inventory_write),
    session: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    service = LotService(session)
    return await service.release_reservation(reservation_id=reservation_id, actor=actor)
