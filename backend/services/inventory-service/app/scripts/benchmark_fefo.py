"""
Module: app.scripts.benchmark_fefo (Inventory Service)
Nhiệm vụ: Kiểm chứng mục 3.12 (NFR-P01, NFR-P06) trên PostgreSQL thật:
          - Seed 10.000 lô hàng vào `stock_lots` (kèm dữ liệu dọn dẹp sau khi đo).
          - Chạy `EXPLAIN (ANALYZE, BUFFERS)` để xác nhận PostgreSQL dùng partial index
            `idx_stock_lots_fefo` trên `(product_id, expiry_date)`.
          - Đo thời gian phản hồi API (`GET /lots`, `GET /stock/summary`,
            `POST /reservations` FEFO) với ngưỡng `GET <= 300 ms`, `FEFO <= 150 ms`.

Cách chạy (từ `backend/services/inventory-service`):
    ../../.venv/Scripts/python.exe -m app.scripts.benchmark_fefo
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
import statistics
import time
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.main import app as inventory_app
from app.models.inventory import Reservation, StockLot, Supplier

TOTAL_LOTS = 10_000
NUM_PRODUCTS = 20
ITERATIONS = 15


async def main() -> None:
    bench_tag = uuid4().hex[:8]
    supplier_id = uuid4()
    product_ids = [uuid4() for _ in range(NUM_PRODUCTS)]
    target_product_id = product_ids[0]
    today = date.today()
    created_reservation_ids = []

    print(f"[1/4] Seeding {TOTAL_LOTS} stock_lots (tag={bench_tag})...")
    async with AsyncSessionLocal() as session:
        session.add(
            Supplier(
                id=supplier_id,
                code=f"BENCH-{bench_tag}",
                name=f"Benchmark Supplier {bench_tag}",
                is_active=True,
            )
        )
        await session.flush()

        lots = []
        for idx in range(TOTAL_LOTS):
            prod_id = product_ids[idx % NUM_PRODUCTS]
            days_offset = (idx % 30) + 1
            lots.append(
                StockLot(
                    id=uuid4(),
                    lot_code=f"BENCH-{bench_tag}-{idx:05d}",
                    product_id=prod_id,
                    supplier_id=supplier_id,
                    quantity_received=Decimal("100.000"),
                    quantity_remaining=Decimal("100.000"),
                    quantity_reserved=Decimal("0.000"),
                    unit_cost=Decimal("20000.00"),
                    received_date=today,
                    expiry_date=today + timedelta(days=days_offset),
                    status="NEAR_EXPIRY" if days_offset <= 3 else "AVAILABLE",
                )
            )
        session.add_all(lots)
        await session.commit()
        await session.execute(text("ANALYZE stock_lots"))
        await session.commit()

    try:
        print("[2/4] Running EXPLAIN (ANALYZE, BUFFERS) on FEFO query...")
        async with AsyncSessionLocal() as session:
            explain_sql = text(
                """
                EXPLAIN (ANALYZE, BUFFERS)
                SELECT id, product_id, expiry_date, quantity_remaining, quantity_reserved
                FROM stock_lots
                WHERE product_id = :pid
                  AND expiry_date >= :today
                  AND status IN ('AVAILABLE', 'NEAR_EXPIRY')
                  AND quantity_remaining > quantity_reserved
                ORDER BY expiry_date ASC, created_at ASC
                FOR UPDATE
                """
            )
            res = await session.execute(
                explain_sql, {"pid": target_product_id, "today": today}
            )
            plan_lines = [row[0] for row in res.fetchall()]
            for line in plan_lines:
                print("  ", line)

        print(f"[3/4] Measuring API latency ({ITERATIONS} iterations each)...")
        headers = {
            "X-Internal-Key": settings.INTERNAL_API_KEY,
            "X-User-Id": str(uuid4()),
            "X-User-Role": "WAREHOUSE",
        }

        get_lots_ms = []
        get_summary_ms = []
        post_fefo_ms = []

        async with AsyncClient(
            transport=ASGITransport(app=inventory_app), base_url="http://bench"
        ) as client:
            for i in range(ITERATIONS):
                t0 = time.perf_counter()
                r1 = await client.get(
                    f"/api/v1/inventory/lots?product_id={target_product_id}&page=1&limit=20",
                    headers=headers,
                )
                assert r1.status_code == 200, r1.text
                get_lots_ms.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                r2 = await client.get(
                    f"/api/v1/inventory/stock/summary?product_id={target_product_id}",
                    headers=headers,
                )
                assert r2.status_code == 200, r2.text
                get_summary_ms.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                r3 = await client.post(
                    "/api/v1/inventory/reservations",
                    headers=headers,
                    json={
                        "order_id": str(uuid4()),
                        "idempotency_key": f"bench-{bench_tag}-{i}",
                        "items": [
                            {"product_id": str(target_product_id), "quantity": "1.000"}
                        ],
                    },
                )
                assert r3.status_code == 200, r3.text
                post_fefo_ms.append((time.perf_counter() - t0) * 1000)
                created_reservation_ids.append(r3.json()["id"])

        def _p95(values):
            ordered = sorted(values)
            idx = max(0, int(0.95 * len(ordered)) - 1)
            return ordered[idx]

        print("\n=== BENCHMARK RESULTS (10,000 lots) ===")
        print(
            f"GET /lots          -> avg={statistics.mean(get_lots_ms):.1f} ms | p95={_p95(get_lots_ms):.1f} ms (target <= 300 ms)"
        )
        print(
            f"GET /stock/summary -> avg={statistics.mean(get_summary_ms):.1f} ms | p95={_p95(get_summary_ms):.1f} ms (target <= 300 ms)"
        )
        print(
            f"POST /reservations -> avg={statistics.mean(post_fefo_ms):.1f} ms | p95={_p95(post_fefo_ms):.1f} ms (target <= 150 ms)"
        )
    finally:
        print("[4/4] Cleaning up benchmark rows...")
        async with AsyncSessionLocal() as session:
            if created_reservation_ids:
                await session.execute(
                    delete(Reservation).where(Reservation.id.in_(created_reservation_ids))
                )
            await session.execute(
                delete(StockLot).where(StockLot.supplier_id == supplier_id)
            )
            await session.execute(
                delete(Supplier).where(Supplier.id == supplier_id)
            )
            await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
