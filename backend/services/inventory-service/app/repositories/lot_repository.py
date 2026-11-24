from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import (
    Reservation,
    ReservationItem,
    StockLot,
    StockMovement,
)


class LotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, lot_id: UUID, for_update: bool = False
    ) -> Optional[StockLot]:
        stmt = select(StockLot).where(StockLot.id == lot_id)
        if for_update:
            bind = self.session.bind
            dialect_name = bind.dialect.name if bind else ""
            if "sqlite" not in dialect_name:
                stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_lots(
        self,
        product_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[StockLot], int]:
        filters = []
        if product_id:
            filters.append(StockLot.product_id == product_id)
        if status:
            filters.append(StockLot.status == status.upper())

        count_stmt = select(func.count(StockLot.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = max(0, (page - 1) * limit)
        stmt = (
            select(StockLot)
            .order_by(StockLot.expiry_date.asc(), StockLot.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_expiring_lots(
        self, days: int = 3, today: Optional[date] = None
    ) -> Tuple[List[StockLot], List[StockLot]]:
        if today is None:
            today = date.today()

        threshold = today + timedelta(days=days)

        near_stmt = (
            select(StockLot)
            .where(
                and_(
                    StockLot.expiry_date >= today,
                    StockLot.expiry_date <= threshold,
                    StockLot.quantity_remaining > 0,
                    StockLot.status != "DEPLETED",
                )
            )
            .order_by(StockLot.expiry_date.asc())
        )
        near_res = await self.session.execute(near_stmt)
        near_expiry_lots = list(near_res.scalars().all())

        expired_stmt = (
            select(StockLot)
            .where(
                and_(
                    StockLot.expiry_date < today,
                    StockLot.quantity_remaining > 0,
                    StockLot.status != "DEPLETED",
                )
            )
            .order_by(StockLot.expiry_date.asc())
        )
        exp_res = await self.session.execute(expired_stmt)
        expired_lots = list(exp_res.scalars().all())

        return near_expiry_lots, expired_lots

    async def get_available_lots_for_fefo(
        self, product_id: UUID, today: Optional[date] = None
    ) -> List[StockLot]:
        if today is None:
            today = date.today()

        stmt = (
            select(StockLot)
            .where(
                and_(
                    StockLot.product_id == product_id,
                    StockLot.expiry_date >= today,
                    StockLot.status.in_(["AVAILABLE", "NEAR_EXPIRY"]),
                    StockLot.quantity_remaining > StockLot.quantity_reserved,
                )
            )
            .order_by(StockLot.expiry_date.asc(), StockLot.created_at.asc())
        )

        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else ""
        if "sqlite" not in dialect_name:
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stock_summary(
        self, product_id: Optional[UUID] = None, today: Optional[date] = None
    ) -> List[Dict]:
        if today is None:
            today = date.today()

        filters = []
        if product_id:
            filters.append(StockLot.product_id == product_id)

        stmt = select(StockLot)
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.session.execute(stmt)
        lots = list(result.scalars().all())

        grouped: Dict[UUID, Dict] = {}
        for lot in lots:
            pid = lot.product_id
            if pid not in grouped:
                grouped[pid] = {
                    "product_id": pid,
                    "total_received": Decimal("0.000"),
                    "total_remaining": Decimal("0.000"),
                    "total_reserved": Decimal("0.000"),
                    "available_quantity": Decimal("0.000"),
                    "active_lots_count": 0,
                    "near_expiry_lots_count": 0,
                    "expired_lots_count": 0,
                }

            item = grouped[pid]
            item["total_received"] += lot.quantity_received
            item["total_remaining"] += lot.quantity_remaining
            item["total_reserved"] += lot.quantity_reserved

            if lot.expiry_date >= today and lot.quantity_remaining > lot.quantity_reserved:
                item["available_quantity"] += (
                    lot.quantity_remaining - lot.quantity_reserved
                )

            if lot.expiry_date < today and lot.quantity_remaining > 0:
                item["expired_lots_count"] += 1
            elif (
                today <= lot.expiry_date <= today + timedelta(days=3)
                and lot.quantity_remaining > 0
            ):
                item["near_expiry_lots_count"] += 1
            elif lot.quantity_remaining > 0:
                item["active_lots_count"] += 1

        return list(grouped.values())

    async def get_reservation_by_id(
        self, reservation_id: UUID, for_update: bool = False
    ) -> Optional[Reservation]:
        stmt = (
            select(Reservation)
            .options(
                selectinload(Reservation.items).selectinload(ReservationItem.lot)
            )
            .where(Reservation.id == reservation_id)
        )
        if for_update:
            bind = self.session.bind
            dialect_name = bind.dialect.name if bind else ""
            if "sqlite" not in dialect_name:
                stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reservation_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[Reservation]:
        stmt = (
            select(Reservation)
            .options(
                selectinload(Reservation.items).selectinload(ReservationItem.lot)
            )
            .where(Reservation.idempotency_key == idempotency_key)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reservation_by_order_id(
        self, order_id: UUID
    ) -> Optional[Reservation]:
        stmt = (
            select(Reservation)
            .options(
                selectinload(Reservation.items).selectinload(ReservationItem.lot)
            )
            .where(Reservation.order_id == order_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_overdue_reservations(
        self, current_time: datetime
    ) -> List[Reservation]:
        stmt = (
            select(Reservation)
            .options(
                selectinload(Reservation.items).selectinload(ReservationItem.lot)
            )
            .where(
                and_(
                    Reservation.status == "ACTIVE",
                    Reservation.expires_at <= current_time,
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add_reservation(self, reservation: Reservation) -> None:
        self.session.add(reservation)

    def add_movement(self, movement: StockMovement) -> None:
        self.session.add(movement)

    async def list_movements(
        self,
        product_id: Optional[UUID] = None,
        lot_id: Optional[UUID] = None,
        movement_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[StockMovement], int]:
        filters = []
        if lot_id:
            filters.append(StockMovement.lot_id == lot_id)
        if movement_type:
            filters.append(StockMovement.movement_type == movement_type.upper())
        if from_date:
            filters.append(
                StockMovement.created_at
                >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
            )
        if to_date:
            filters.append(
                StockMovement.created_at
                <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)
            )
        if product_id:
            filters.append(
                StockMovement.lot_id.in_(
                    select(StockLot.id).where(StockLot.product_id == product_id)
                )
            )

        count_stmt = select(func.count(StockMovement.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = max(0, (page - 1) * limit)
        stmt = (
            select(StockMovement)
            .order_by(StockMovement.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
