"""
Module: app.main (Catalog Service)
Nhiệm vụ: Điểm khởi chạy chính (Entrypoint) của Catalog Service tại cổng 8002.
          - Đăng ký bộ xử lý lỗi chuẩn `{code, message, details}`.
          - Cung cấp `/health` kiểm tra kết nối DB thực tế (`SELECT 1`) tới `fruitstore_catalog_db` (NFR-O03).
          - Định tuyến `/api/v1/catalog/*`.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.catalog import router as catalog_router
from app.core.config import settings
from app.core.exceptions import AppError, register_exception_handlers
from app.db.session import get_db

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.3.0",
    description=(
        "Dịch vụ Danh mục & Sản phẩm (Catalog Service) thuộc kiến trúc SOA FruitStore. "
        "Sở hữu độc lập cơ sở dữ liệu `fruitstore_catalog_db`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

register_exception_handlers(app)
app.include_router(catalog_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"], summary="Kiểm tra trạng thái Catalog Service và kết nối DB")
async def health_check(session: AsyncSession = Depends(get_db)) -> dict:
    """Thực thi `SELECT 1` xuống `fruitstore_catalog_db` để kiểm tra sức khỏe thực tế của service."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Không thể kết nối tới cơ sở dữ liệu fruitstore_catalog_db.",
            details={"reason": str(exc)},
        ) from exc

    return {
        "status": "healthy",
        "service": "catalog-service",
        "database": "fruitstore_catalog_db",
    }

