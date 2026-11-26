import os
import pytest
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_inventory_e2e_via_gateway_smoke():
    """Kiểm tra luồng tồn kho & FEFO đi qua API Gateway khi dịch vụ đang chạy."""
    headers = {
        "X-User-Id": os.getenv("TEST_USER_ID", "11111111-1111-1111-1111-111111111111"),
        "X-User-Role": os.getenv("TEST_USER_ROLE", "WAREHOUSE"),
    }
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        try:
            resp = await client.get("/api/v1/inventory/stock/summary", headers=headers)
        except httpx.ConnectError:
            pytest.skip(f"Gateway chưa chạy tại {GATEWAY_URL} — bỏ qua khi chạy offline")

        assert resp.status_code in (200, 401, 403)
