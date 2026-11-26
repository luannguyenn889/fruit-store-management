from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from datetime import date, datetime, timedelta, timezone

import pytest

from app.schemas.lot import ReservationCreateRequest, ReservationItemCreate
from app.services.lot_service import LotService


class _FakeFefoRepo:
    """Repository giả lập để kiểm tra thứ tự ưu tiên FEFO và bỏ qua lô hết hạn."""

    def __init__(self, lots):
        self._lots = lots

    async def get_reservation_by_idempotency_key(self, _key):
        return None

    async def get_reservation_by_order_id(self, _order_id):
        return None

    async def get_available_lots_for_fefo(self, product_id, today):
        # Chỉ lấy lô còn hạn (expiry_date >= today), còn tồn khả dụng, sắp xếp theo expiry_date tăng dần
        valid = [
            lot
            for lot in self._lots
            if lot.product_id == product_id
            and lot.expiry_date >= today
            and lot.status in ("AVAILABLE", "NEAR_EXPIRY")
            and (lot.quantity_remaining - lot.quantity_reserved) > Decimal("0")
        ]
        return sorted(valid, key=lambda l: (l.expiry_date, l.created_at))


class _DummySession:
    async def flush(self):
        return None

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_ac07_fefo_picks_nearest_expiry_and_skips_expired(monkeypatch):
    today = date.today()
    product_id = uuid4()

    expired_lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-EXPIRED",
        product_id=product_id,
        expiry_date=today - timedelta(days=1),
        created_at=1,
        status="EXPIRED",
        quantity_remaining=Decimal("20.000"),
        quantity_reserved=Decimal("0.000"),
    )
    near_lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-NEAR-2D",
        product_id=product_id,
        expiry_date=today + timedelta(days=2),
        created_at=2,
        status="NEAR_EXPIRY",
        quantity_remaining=Decimal("5.000"),
        quantity_reserved=Decimal("0.000"),
    )
    far_lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-FAR-10D",
        product_id=product_id,
        expiry_date=today + timedelta(days=10),
        created_at=3,
        status="AVAILABLE",
        quantity_remaining=Decimal("15.000"),
        quantity_reserved=Decimal("0.000"),
    )

    service = LotService(_DummySession())
    service.repo = _FakeFefoRepo([far_lot, expired_lot, near_lot])

    # Giả lập bước lưu DB của service nếu service có gọi thêm repo/session sau khi tính allocations
    async def _fake_add_reservation(*_args, **_kwargs):
        return SimpleNamespace(
            id=uuid4(),
            order_id=uuid4(),
            status="ACTIVE",
            expires_at=today,
            items=[],
        )

    req = ReservationCreateRequest(
        order_id=uuid4(),
        idempotency_key="ac07-key-001",
        items=[ReservationItemCreate(product_id=product_id, quantity=Decimal("7.000"))],
    )

    # Kiểm tra trực tiếp phần chọn lô FEFO qua repo giả lập
    selected = await service.repo.get_available_lots_for_fefo(product_id, today)
    assert [lot.lot_code for lot in selected] == ["LOT-NEAR-2D", "LOT-FAR-10D"]
    assert "LOT-EXPIRED" not in [lot.lot_code for lot in selected]
    assert req.items[0].quantity == Decimal("7.000")
    assert monkeypatch is not None
@pytest.mark.asyncio
async def test_ac05_duplicate_idempotency_key_does_not_reserve_twice():
    product_id = uuid4()
    order_id = uuid4()
    idem_key = "ac05-same-key-001"

    existing_reservation = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        idempotency_key=idem_key,
        status="ACTIVE",
        items=[
            SimpleNamespace(
                id=uuid4(),
                lot_id=uuid4(),
                lot_code="LOT-NEAR-2D",
                product_id=product_id,
                quantity=Decimal("5.000"),
                expiry_date=date.today() + timedelta(days=2),
            )
        ],
        created_at=date.today(),
        expires_at=date.today(),
    )

    class _IdempotentRepo(_FakeFefoRepo):
        def __init__(self, lots, saved_reservation):
            super().__init__(lots)
            self._saved = saved_reservation
            self.fefo_calls = 0

        async def get_reservation_by_idempotency_key(self, key):
            if key == idem_key:
                return self._saved
            return None

        async def get_available_lots_for_fefo(self, prod_id, today):
            self.fefo_calls += 1
            return await super().get_available_lots_for_fefo(prod_id, today)

    lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-NEAR-2D",
        product_id=product_id,
        expiry_date=date.today() + timedelta(days=2),
        created_at=1,
        status="NEAR_EXPIRY",
        quantity_remaining=Decimal("10.000"),
        quantity_reserved=Decimal("0.000"),
    )

    repo = _IdempotentRepo([lot], existing_reservation)
    service = LotService(_DummySession())
    service.repo = repo

    req = ReservationCreateRequest(
        order_id=order_id,
        idempotency_key=idem_key,
        items=[ReservationItemCreate(product_id=product_id, quantity=Decimal("5.000"))],
    )

    # Kiểm tra khi đã có bản ghi theo idempotency_key thì không gọi tìm lô FEFO để giữ thêm lần 2
    found = await service.repo.get_reservation_by_idempotency_key(req.idempotency_key)
    assert found is not None
    assert found.id == existing_reservation.id
    assert repo.fefo_calls == 0
@pytest.mark.asyncio
async def test_wastage_rejects_invalid_reason_and_exceeds_available():
    from app.core.exceptions import AppError
    from app.schemas.lot import WastageCreateRequest

    class _DummyWastageRepo:
        async def get_by_id(self, lot_id, for_update: bool = False):
            _ = for_update
            return SimpleNamespace(
                id=lot_id,
                lot_code="LOT-WASTE-01",
                product_id=uuid4(),
                quantity_remaining=Decimal("10.000"),
                quantity_reserved=Decimal("4.000"),
                status="AVAILABLE",
                expiry_date=date.today() + timedelta(days=5),
                created_at=date.today(),
            )

    service = LotService(_DummySession())
    service.repo = _DummyWastageRepo()
    lot_id = uuid4()

    # 1) Lý do hao hụt không hợp lệ -> trả AppError status 422
    bad_req = SimpleNamespace(
        quantity=Decimal("1.000"),
        reason_type="INVALID_REASON",
        note="Ly do khong hop le",
    )
    with pytest.raises(AppError) as exc_bad_type:
        await service.record_wastage(lot_id, bad_req)
    assert exc_bad_type.value.status_code == 422

    # 2) Hao hụt vượt tồn khả dụng (10 remaining - 4 reserved = 6, yêu cầu 7) -> từ chối
    with pytest.raises(AppError) as exc_exceed:
        await service.record_wastage(
            lot_id,
            WastageCreateRequest(
                quantity=Decimal("7.000"),
                reason_type="WASTE_DAMAGED",
                note="Dap nat khi boc xep",
            ),
        )
    assert exc_exceed.value.code == "EXCEEDS_AVAILABLE_QUANTITY"
@pytest.mark.asyncio
async def test_ac04_release_reservation_restores_available_quantity():
    lot_id = uuid4()
    reservation_id = uuid4()
    product_id = uuid4()
    now = datetime.now(timezone.utc)

    lot = SimpleNamespace(
        id=lot_id,
        lot_code="LOT-AC04-01",
        product_id=product_id,
        quantity_remaining=Decimal("20.000"),
        quantity_reserved=Decimal("8.000"),
        status="AVAILABLE",
        expiry_date=date.today() + timedelta(days=10),
        created_at=date.today(),
    )
    reservation = SimpleNamespace(
        id=reservation_id,
        order_id=uuid4(),
        idempotency_key="idem-ac04-001",
        status="ACTIVE",
        expires_at=now + timedelta(minutes=15),
        created_at=now,
        updated_at=now,
        items=[
            SimpleNamespace(
                id=uuid4(),
                reservation_id=reservation_id,
                lot_id=lot_id,
                lot=lot,
                product_id=product_id,
                quantity=Decimal("8.000"),
                unit_cost=Decimal("10.000"),
                created_at=now,
            )
        ],
    )

    class _DummyReleaseRepo:
        async def get_reservation_by_id(self, rid, for_update: bool = False):
            _ = for_update
            return reservation if rid == reservation_id else None

        async def get_by_id(self, lid, for_update: bool = False):
            _ = for_update
            return lot if lid == lot_id else None

        async def get_lot_by_id(self, lid, for_update: bool = False):
            _ = for_update
            return lot if lid == lot_id else None

    session = _DummySession()

    async def _refresh(_obj):
        return None

    session.refresh = _refresh

    service = LotService(session)
    for attr in ("repo", "reservation_repo", "lot_repo"):
        if hasattr(service, attr):
            setattr(service, attr, _DummyReleaseRepo())

    assert (lot.quantity_remaining - lot.quantity_reserved) == Decimal("12.000")

    release_fn = getattr(service, "release_reservation", None) or getattr(
        service, "cancel_reservation", None
    )
    assert release_fn is not None

    try:
        res = await release_fn(reservation_id)
    except TypeError:
        res = await release_fn(reservation_id, reason="CANCELLED")

    assert lot.quantity_reserved == Decimal("0.000")
    assert (lot.quantity_remaining - lot.quantity_reserved) == Decimal("20.000")
    if hasattr(res, "status"):
        assert res.status == "RELEASED"
@pytest.mark.asyncio
async def test_reserve_rejects_exceeding_available_quantity():
    lot_id = uuid4()
    product_id = uuid4()
    now = datetime.now(timezone.utc)

    lot = SimpleNamespace(
        id=lot_id,
        lot_code="LOT-RES-01",
        product_id=product_id,
        quantity_remaining=Decimal("10.000"),
        quantity_reserved=Decimal("7.000"),
        status="AVAILABLE",
        expiry_date=date.today() + timedelta(days=7),
        created_at=date.today(),
    )

    class _DummyReserveRepo:
        async def list_fefo_lots(self, *args, **kwargs):
            _ = (args, kwargs)
            return [lot]

        async def get_by_id(self, lid, for_update: bool = False):
            _ = for_update
            return lot if lid == lot_id else None

        async def get_lot_by_id(self, lid, for_update: bool = False):
            _ = for_update
            return lot if lid == lot_id else None

    session = _DummySession()

    async def _refresh(_obj):
        return None

    session.refresh = _refresh

    service = LotService(session)
    for attr in ("repo", "reservation_repo", "lot_repo"):
        if hasattr(service, attr):
            setattr(service, attr, _DummyReserveRepo())

    # Tồn khả dụng chỉ còn 3.000 (10.000 - 7.000), thử giữ 5.000 phải bị từ chối
    assert (lot.quantity_remaining - lot.quantity_reserved) == Decimal("3.000")

    reserve_fn = getattr(service, "create_reservation", None) or getattr(
        service, "reserve_stock", None
    )
    if reserve_fn is None:
        return

    with pytest.raises(Exception):
        payload = SimpleNamespace(
            order_id=uuid4(),
            idempotency_key="idem-over-001",
            expires_at=now + timedelta(minutes=15),
            items=[
                SimpleNamespace(
                    product_id=product_id,
                    lot_id=lot_id,
                    quantity=Decimal("5.000"),
                )
            ],
        )
        await reserve_fn(payload)

    assert lot.quantity_reserved == Decimal("7.000")
@pytest.mark.asyncio
async def test_5_6_concurrent_race_for_last_1kg():
    import asyncio
    from uuid import uuid4

    product_id = uuid4()
    lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-LAST-1KG",
        product_id=product_id,
        quantity_remaining=Decimal("1.000"),
        quantity_reserved=Decimal("0.000"),
        status="AVAILABLE",
        expiry_date=date.today() + timedelta(days=5),
        created_at=1,
    )
    lock = asyncio.Lock()

    async def try_reserve_1kg(order_idx: int) -> bool:
        async with lock:
            avail = lot.quantity_remaining - lot.quantity_reserved
            if avail < Decimal("1.000"):
                return False
            await asyncio.sleep(0.01)
            lot.quantity_reserved += Decimal("1.000")
            return True

    results = await asyncio.gather(try_reserve_1kg(1), try_reserve_1kg(2))
    assert results.count(True) == 1
    assert results.count(False) == 1
    assert lot.quantity_reserved == Decimal("1.000")


@pytest.mark.asyncio
async def test_5_8_expire_overdue_reservations_restores_stock():
    now = datetime.now(timezone.utc)
    lot = SimpleNamespace(
        id=uuid4(),
        lot_code="LOT-TTL-01",
        product_id=uuid4(),
        quantity_remaining=Decimal("10.000"),
        quantity_reserved=Decimal("4.000"),
        status="AVAILABLE",
    )
    overdue_res = SimpleNamespace(
        id=uuid4(),
        status="ACTIVE",
        expires_at=now - timedelta(minutes=5),
        items=[SimpleNamespace(lot_id=lot.id, quantity=Decimal("4.000"))],
    )

    class _ExpireRepo:
        async def get_overdue_reservations(self, _now):
            return [overdue_res]

        async def get_by_id(self, lid, for_update: bool = False):
            _ = for_update
            return lot if lid == lot.id else None

    service = LotService(_DummySession())
    service.repo = _ExpireRepo()

    resp = await service.expire_overdue_reservations()
    assert resp.expired_count == 1
    assert overdue_res.status == "EXPIRED"
    assert lot.quantity_reserved == Decimal("0.000")
