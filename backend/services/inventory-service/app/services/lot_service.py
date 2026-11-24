from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import Actor
from app.core.exceptions import AppError
from app.models.inventory import (
    Reservation,
    ReservationItem,
    StockLot,
    StockMovement,
)
from app.repositories.lot_repository import LotRepository
from app.schemas.lot import (
    AdjustmentCreateRequest,
    ExpireOverdueResponse,
    ExpiringLotsResponse,
    LotListResponse,
    LotResponse,
    ProductStockSummary,
    ReservationCreateRequest,
    ReservationItemResponse,
    ReservationResponse,
    StockMovementListResponse,
    StockMovementResponse,
    StockSummaryResponse,
    WastageCreateRequest,
)


class LotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LotRepository(session)

    @staticmethod
    def _refresh_lot_status(lot: StockLot, today: date) -> str:
        if lot.quantity_remaining <= Decimal("0.000"):
            status = "DEPLETED"
        elif lot.expiry_date < today:
            status = "EXPIRED"
        elif lot.expiry_date <= today + timedelta(
            days=getattr(settings, "NEAR_EXPIRY_DAYS", 3)
        ):
            status = "NEAR_EXPIRY"
        else:
            status = "AVAILABLE"

        lot.status = status
        return status

    def _to_lot_response(self, lot: StockLot, today: Optional[date] = None) -> LotResponse:
        if today is None:
            today = date.today()

        self._refresh_lot_status(lot, today)
        avail = max(Decimal("0.000"), lot.quantity_remaining - lot.quantity_reserved)
        days_left = (lot.expiry_date - today).days

        return LotResponse(
            id=lot.id,
            lot_code=lot.lot_code,
            product_id=lot.product_id,
            supplier_id=lot.supplier_id,
            purchase_order_id=lot.purchase_order_id,
            quantity_received=lot.quantity_received,
            quantity_remaining=lot.quantity_remaining,
            quantity_reserved=lot.quantity_reserved,
            available_quantity=avail,
            unit_cost=lot.unit_cost,
            received_date=lot.received_date,
            expiry_date=lot.expiry_date,
            status=lot.status,
            days_until_expiry=days_left,
            is_expired=(lot.expiry_date < today),
            created_at=lot.created_at,
            updated_at=lot.updated_at,
        )

    def _to_reservation_response(self, reservation: Reservation) -> ReservationResponse:
        items = [
            ReservationItemResponse(
                id=item.id,
                reservation_id=item.reservation_id,
                lot_id=item.lot_id,
                lot_code=item.lot.lot_code if item.lot else "",
                product_id=item.product_id,
                quantity=item.quantity,
                expiry_date=item.lot.expiry_date if item.lot else date.today(),
            )
            for item in reservation.items
        ]

        return ReservationResponse(
            id=reservation.id,
            order_id=reservation.order_id,
            idempotency_key=reservation.idempotency_key,
            status=reservation.status,
            expires_at=reservation.expires_at,
            created_at=reservation.created_at,
            items=items,
        )

    async def list_lots(
        self,
        product_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> LotListResponse:
        today = date.today()
        lots, total = await self.repo.list_lots(
            product_id=product_id, status=status, page=page, limit=limit
        )
        items = [self._to_lot_response(lot, today) for lot in lots]
        pages = ceil(total / limit) if limit > 0 else 1

        return LotListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_lot_by_id(self, lot_id: UUID) -> LotResponse:
        lot = await self.repo.get_by_id(lot_id)
        if not lot:
            raise AppError(
                status_code=404,
                code="LOT_NOT_FOUND",
                message=f"Khong tim thay lo hang {lot_id}.",
            )
        return self._to_lot_response(lot)

    async def get_stock_summary(
        self, product_id: Optional[UUID] = None
    ) -> StockSummaryResponse:
        today = date.today()
        raw_summaries = await self.repo.get_stock_summary(
            product_id=product_id, today=today
        )

        total_avail = Decimal("0.000")
        total_res = Decimal("0.000")
        total_rem = Decimal("0.000")
        products = []

        for row in raw_summaries:
            total_avail += row["available_quantity"]
            total_res += row["total_reserved"]
            total_rem += row["total_remaining"]
            products.append(ProductStockSummary(**row))

        return StockSummaryResponse(
            total_products=len(products),
            total_available_quantity=total_avail,
            total_reserved_quantity=total_res,
            total_remaining_quantity=total_rem,
            products=products,
        )

    async def get_expiring_lots(self, days: int = 3) -> ExpiringLotsResponse:
        today = date.today()
        near_lots, expired_lots = await self.repo.get_expiring_lots(
            days=days, today=today
        )

        return ExpiringLotsResponse(
            days_threshold=days,
            total_near_expiry=len(near_lots),
            total_expired=len(expired_lots),
            near_expiry_lots=[self._to_lot_response(l, today) for l in near_lots],
            expired_lots=[self._to_lot_response(l, today) for l in expired_lots],
        )

    async def create_reservation(
        self, req: ReservationCreateRequest, actor: Optional[Actor] = None
    ) -> ReservationResponse:
        existing = await self.repo.get_reservation_by_idempotency_key(
            req.idempotency_key
        )
        if existing:
            return self._to_reservation_response(existing)

        existing_order = await self.repo.get_reservation_by_order_id(req.order_id)
        if existing_order and existing_order.status == "ACTIVE":
            return self._to_reservation_response(existing_order)

        today = date.today()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.RESERVATION_TTL_MINUTES)

        allocations: List[tuple[StockLot, Decimal, UUID]] = []

        for item in req.items:
            needed = item.quantity
            available_lots = await self.repo.get_available_lots_for_fefo(
                product_id=item.product_id, today=today
            )

            total_available = sum(
                (lot.quantity_remaining - lot.quantity_reserved)
                for lot in available_lots
            )

            if total_available < needed:
                raise AppError(
                    status_code=400,
                    code="INSUFFICIENT_STOCK",
                    message=(
                        f"San pham {item.product_id} khong du ton kha dung. "
                        f"Yeu cau: {needed} kg, Kha dung con lai: {total_available} kg."
                    ),
                    details={
                        "product_id": str(item.product_id),
                        "requested": str(needed),
                        "available": str(total_available),
                    },
                )

            for lot in available_lots:
                lot_avail = lot.quantity_remaining - lot.quantity_reserved
                if lot_avail <= Decimal("0.000"):
                    continue

                take = min(needed, lot_avail)
                allocations.append((lot, take, item.product_id))
                needed -= take

                if needed <= Decimal("0.000"):
                    break

        reservation = Reservation(
            order_id=req.order_id,
            idempotency_key=req.idempotency_key,
            status="ACTIVE",
            expires_at=expires_at,
        )
        self.repo.add_reservation(reservation)
        await self.session.flush()

        for lot, qty, pid in allocations:
            lot.quantity_reserved += qty
            res_item = ReservationItem(
                reservation_id=reservation.id,
                lot_id=lot.id,
                product_id=pid,
                quantity=qty,
            )
            self.session.add(res_item)

        await self.session.commit()
        await self.session.refresh(reservation)

        full_reservation = await self.repo.get_reservation_by_id(reservation.id)
        return self._to_reservation_response(full_reservation or reservation)

    async def commit_reservation(
        self, reservation_id: UUID, actor: Optional[Actor] = None
    ) -> ReservationResponse:
        reservation = await self.repo.get_reservation_by_id(
            reservation_id, for_update=True
        )
        if not reservation:
            raise AppError(
                status_code=404,
                code="RESERVATION_NOT_FOUND",
                message=f"Khong tim thay phieu giu hang {reservation_id}.",
            )

        if reservation.status == "COMMITTED":
            return self._to_reservation_response(reservation)

        if reservation.status != "ACTIVE":
            raise AppError(
                status_code=400,
                code="INVALID_RESERVATION_STATUS",
                message=f"Phieu giu hang o trang thai {reservation.status}, khong the commit.",
            )

        today = date.today()
        for item in reservation.items:
            lot = await self.repo.get_by_id(item.lot_id, for_update=True)
            if not lot:
                continue

            lot.quantity_reserved -= item.quantity
            lot.quantity_remaining -= item.quantity
            self._refresh_lot_status(lot, today)

            movement = StockMovement(
                lot_id=lot.id,
                movement_type="SALE_OUT",
                quantity_change=-item.quantity,
                unit_cost_snapshot=lot.unit_cost,
                reference_type="ORDER",
                reference_id=reservation.order_id,
                reason=f"Xuat kho ban hang don {reservation.order_id}",
                performed_by_user_id=actor.id if actor else None,
            )
            self.repo.add_movement(movement)

        reservation.status = "COMMITTED"
        await self.session.commit()
        await self.session.refresh(reservation)

        full_res = await self.repo.get_reservation_by_id(reservation.id)
        return self._to_reservation_response(full_res or reservation)

    async def release_reservation(
        self, reservation_id: UUID, actor: Optional[Actor] = None
    ) -> ReservationResponse:
        reservation = await self.repo.get_reservation_by_id(
            reservation_id, for_update=True
        )
        if not reservation:
            raise AppError(
                status_code=404,
                code="RESERVATION_NOT_FOUND",
                message=f"Khong tim thay phieu giu hang {reservation_id}.",
            )

        if reservation.status == "RELEASED":
            return self._to_reservation_response(reservation)

        if reservation.status != "ACTIVE":
            raise AppError(
                status_code=400,
                code="INVALID_RESERVATION_STATUS",
                message=f"Phieu giu hang o trang thai {reservation.status}, khong the release.",
            )

        for item in reservation.items:
            lot = await self.repo.get_by_id(item.lot_id, for_update=True)
            if lot:
                lot.quantity_reserved = max(
                    Decimal("0.000"), lot.quantity_reserved - item.quantity
                )

        reservation.status = "RELEASED"
        await self.session.commit()
        await self.session.refresh(reservation)

        full_res = await self.repo.get_reservation_by_id(reservation.id)
        return self._to_reservation_response(full_res or reservation)

    async def expire_overdue_reservations(self) -> ExpireOverdueResponse:
        now = datetime.now(timezone.utc)
        overdue_list = await self.repo.get_overdue_reservations(now)

        expired_ids = []
        for reservation in overdue_list:
            for item in reservation.items:
                lot = await self.repo.get_by_id(item.lot_id, for_update=True)
                if lot:
                    lot.quantity_reserved = max(
                        Decimal("0.000"), lot.quantity_reserved - item.quantity
                    )

            reservation.status = "EXPIRED"
            expired_ids.append(reservation.id)

        if expired_ids:
            await self.session.commit()

        return ExpireOverdueResponse(
            expired_count=len(expired_ids),
            expired_reservation_ids=expired_ids,
            message=f"Da giai phong {len(expired_ids)} phieu giu hang het han.",
        )

    async def record_wastage(
        self, lot_id: UUID, req: WastageCreateRequest, actor: Optional[Actor] = None
    ) -> LotResponse:
        if req.reason_type not in ["WASTE_EXPIRED", "WASTE_DAMAGED"]:
            raise AppError(
                status_code=422,
                code="INVALID_WASTE_REASON",
                message="Ly do hao hut khong hop le.",
            )

        lot = await self.repo.get_by_id(lot_id, for_update=True)
        if not lot:
            raise AppError(
                status_code=404,
                code="LOT_NOT_FOUND",
                message=f"Khong tim thay lo hang {lot_id}.",
            )

        available_in_lot = lot.quantity_remaining - lot.quantity_reserved
        if req.quantity > available_in_lot:
            raise AppError(
                status_code=400,
                code="EXCEEDS_AVAILABLE_QUANTITY",
                message=f"So luong hao hut ({req.quantity} kg) vuot qua ton kha dung con lai ({available_in_lot} kg).",
                details={
                    "requested_waste": str(req.quantity),
                    "available_in_lot": str(available_in_lot),
                },
            )

        lot.quantity_remaining -= req.quantity
        today = date.today()
        self._refresh_lot_status(lot, today)

        movement = StockMovement(
            lot_id=lot.id,
            movement_type=req.reason_type,
            quantity_change=-req.quantity,
            unit_cost_snapshot=lot.unit_cost,
            reference_type="MANUAL_CHECK",
            reason=req.note,
            performed_by_user_id=actor.id if actor else None,
        )
        self.repo.add_movement(movement)

        await self.session.commit()
        await self.session.refresh(lot)

        return self._to_lot_response(lot, today)

    async def adjust_stock(
        self, lot_id: UUID, req: AdjustmentCreateRequest, actor: Optional[Actor] = None
    ) -> LotResponse:
        lot = await self.repo.get_by_id(lot_id, for_update=True)
        if not lot:
            raise AppError(
                status_code=404,
                code="LOT_NOT_FOUND",
                message=f"Khong tim thay lo hang {lot_id}.",
            )

        if req.actual_quantity < lot.quantity_reserved:
            raise AppError(
                status_code=400,
                code="ADJUSTMENT_CONFLICT_WITH_RESERVATION",
                message="Khong the dieu chinh so luong thap hon so luong dang giu.",
            )

        diff = req.actual_quantity - lot.quantity_remaining
        lot.quantity_remaining = req.actual_quantity
        today = date.today()
        self._refresh_lot_status(lot, today)

        if diff != Decimal("0.000"):
            movement = StockMovement(
                lot_id=lot.id,
                movement_type="ADJUSTMENT",
                quantity_change=diff,
                unit_cost_snapshot=lot.unit_cost,
                reference_type="MANUAL_CHECK",
                reason=req.reason,
                performed_by_user_id=actor.id if actor else None,
            )
            self.repo.add_movement(movement)

        await self.session.commit()
        await self.session.refresh(lot)

        return self._to_lot_response(lot, today)

    async def list_movements(
        self,
        product_id: Optional[UUID] = None,
        lot_id: Optional[UUID] = None,
        movement_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> StockMovementListResponse:
        movements, total = await self.repo.list_movements(
            product_id=product_id,
            lot_id=lot_id,
            movement_type=movement_type,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )

        items = [
            StockMovementResponse(
                id=m.id,
                lot_id=m.lot_id,
                movement_type=m.movement_type,
                quantity_change=m.quantity_change,
                unit_cost_snapshot=m.unit_cost_snapshot,
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                idempotency_key=m.idempotency_key,
                reason=m.reason,
                performed_by_user_id=m.performed_by_user_id,
                created_at=m.created_at,
            )
            for m in movements
        ]
        pages = ceil(total / limit) if limit > 0 else 1

        return StockMovementListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
