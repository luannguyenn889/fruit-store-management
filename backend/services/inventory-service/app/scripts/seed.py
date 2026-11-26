import asyncio
import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.inventory import Supplier
from datetime import date, timedelta
from decimal import Decimal
from app.models.inventory import StockLot

SUPPLIERS_SEED = [
    {
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.supplier.NCC-001"),
        "code": "NCC-001",
        "name": "Nhà cung cấp Trái cây Miền Tây",
        "phone": "0901111001",
        "address": "Cần Thơ",
        "is_active": True,
    },
    {
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.supplier.NCC-002"),
        "code": "NCC-002",
        "name": "Nhà cung cấp Nông sản Cao Nguyên",
        "phone": "0901111002",
        "address": "Đà Lạt",
        "is_active": True,
    },
]


async def seed_suppliers() -> None:
    async with AsyncSessionLocal() as session:
        for item in SUPPLIERS_SEED:
            existing = (
                await session.execute(select(Supplier).where(Supplier.code == item["code"]))
            ).scalar_one_or_none()
            if existing is None:
                session.add(Supplier(**item))
        await session.commit()

SAMPLE_PRODUCT_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.product.SAMPLE-001")

def build_lots_seed(today: date, supplier_id: uuid.UUID) -> list[dict]:
    return [
        {
            "id": uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.lot.LOT-FRESH-01"),
            "lot_code": "LOT-FRESH-01",
            "product_id": SAMPLE_PRODUCT_ID,
            "supplier_id": supplier_id,
            "quantity_received": Decimal("50.000"),
            "quantity_remaining": Decimal("50.000"),
            "quantity_reserved": Decimal("0.000"),
            "unit_cost": Decimal("35000.00"),
            "received_date": today,
            "expiry_date": today + timedelta(days=10),
            "status": "AVAILABLE",
        },
        {
            "id": uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.lot.LOT-NEAR-01"),
            "lot_code": "LOT-NEAR-01",
            "product_id": SAMPLE_PRODUCT_ID,
            "supplier_id": supplier_id,
            "quantity_received": Decimal("20.000"),
            "quantity_remaining": Decimal("20.000"),
            "quantity_reserved": Decimal("0.000"),
            "unit_cost": Decimal("30000.00"),
            "received_date": today,
            "expiry_date": today + timedelta(days=2),
            "status": "NEAR_EXPIRY",
        },
        {
            "id": uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.lot.LOT-EXP-01"),
            "lot_code": "LOT-EXP-01",
            "product_id": SAMPLE_PRODUCT_ID,
            "supplier_id": supplier_id,
            "quantity_received": Decimal("10.000"),
            "quantity_remaining": Decimal("10.000"),
            "quantity_reserved": Decimal("0.000"),
            "unit_cost": Decimal("25000.00"),
            "received_date": today - timedelta(days=10),
            "expiry_date": today - timedelta(days=1),
            "status": "EXPIRED",
        },
    ]

async def seed_lots() -> None:
    today = date.today()
    default_supplier_id = uuid.uuid5(uuid.NAMESPACE_DNS, "fruitstore.supplier.NCC-001")
    async with AsyncSessionLocal() as session:
        for item in build_lots_seed(today, default_supplier_id):
            existing = (
                await session.execute(select(StockLot).where(StockLot.lot_code == item["lot_code"]))
            ).scalar_one_or_none()
            if existing is None:
                session.add(StockLot(**item))
        await session.commit()

async def main() -> None:
    await seed_suppliers()
    await seed_lots()


if __name__ == "__main__":
    asyncio.run(main())