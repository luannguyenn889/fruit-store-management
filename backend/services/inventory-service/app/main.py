"""
Module: app.main (Inventory Service)
Nhiệm vụ: Điểm khởi chạy chính (Entrypoint) của Inventory Service tại cổng 8003:
          - Đăng ký bộ xử lý lỗi chuẩn `{code, message, details}`.
          - Middleware tiếp nhận, ghi log và phản hồi `X-Request-ID` (NFR-O01).
          - Cung cấp `/health` và `/api/v1/inventory/health` kiểm tra kết nối DB thực tế
            (`SELECT 1`) tới `fruitstore_inventory_db` (FR-H02, NFR-O03).
          - Sẵn sàng gắn router `procurement` (TV2) và `lots` (TV3) vào `/api/v1`.
"""

import logging
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, register_exception_handlers
from app.db.session import get_db

logger = logging.getLogger("inventory-service")

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description=(
        "Dịch vụ Kho & Quản lý Lô hàng FEFO (Inventory Service) thuộc kiến trúc SOA FruitStore. "
        "Sở hữu độc lập cơ sở dữ liệu `fruitstore_inventory_db`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

register_exception_handlers(app)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Tiếp nhận hoặc khởi tạo `X-Request-ID` để truy vết log phân tán (NFR-O01)."""
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    logger.info("[%s] %s %s", request_id, request.method, request.url.path)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


from app.api.v1.lots import router as lots_router
from app.api.v1.procurement import router as procurement_router

app.include_router(procurement_router, prefix=settings.API_V1_STR)
app.include_router(lots_router, prefix=settings.API_V1_STR)


async def _check_db_health(session: AsyncSession) -> dict:
    """Thực thi `SELECT 1` xuống `fruitstore_inventory_db` để kiểm tra sức khỏe thực tế."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Không thể kết nối tới cơ sở dữ liệu fruitstore_inventory_db.",
            details={"reason": str(exc)},
        ) from exc

    return {
        "status": "healthy",
        "service": "inventory-service",
        "database": "fruitstore_inventory_db",
    }


@app.get(
    "/health",
    tags=["Health Check"],
    summary="Kiểm tra trạng thái Inventory Service và kết nối DB",
)
async def health_check(session: AsyncSession = Depends(get_db)) -> dict:
    """Endpoint health check nội bộ tại `/health`."""
    return await _check_db_health(session)


@app.get(
    f"{settings.API_V1_STR}/inventory/health",
    tags=["Health Check"],
    summary="Kiểm tra trạng thái Inventory Service thông qua API Gateway",
)
async def gateway_health_check(session: AsyncSession = Depends(get_db)) -> dict:
    """Endpoint health check định tuyến qua Gateway `/api/v1/inventory/health`."""
    return await _check_db_health(session)
