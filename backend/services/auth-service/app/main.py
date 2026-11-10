"""
Module: app.main
Nhiệm vụ: Điểm khởi chạy chính (Entrypoint) của Auth Service (cổng 8001).
          - Đăng ký bộ xử lý ngoại lệ chuẩn `{code, message, details}`.
          - Cung cấp endpoint `/health` kiểm tra kết nối thực tế tới `fruitstore_auth_db` (`SELECT 1`).
          - Định tuyến `/api/v1/auth/*`.
          - Không tự động gọi `create_all()` hay seed ngầm khi khởi động (tuân thủ NFR-M02).
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.core.exceptions import AppError, register_exception_handlers
from app.db.session import get_db

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.3.0",
    description=(
        "Dịch vụ Xác thực & Phân quyền (Auth Service) thuộc kiến trúc SOA FruitStore. "
        "Sở hữu độc lập cơ sở dữ liệu `fruitstore_auth_db`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Đăng ký bộ xử lý lỗi chuẩn hóa JSON
register_exception_handlers(app)

# Gắn router xác thực vào tiền tố /api/v1
app.include_router(auth_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"], summary="Kiểm tra trạng thái Auth Service và kết nối DB")
async def health_check(session: AsyncSession = Depends(get_db)) -> dict:
    """
    Thực hiện truy vấn `SELECT 1` thật xuống `fruitstore_auth_db` để đảm bảo
    service và kết nối cơ sở dữ liệu đều sẵn sàng (NFR-O03).
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Không thể kết nối tới cơ sở dữ liệu fruitstore_auth_db.",
            details={"reason": str(exc)},
        ) from exc

    return {
        "status": "healthy",
        "service": "auth-service",
        "database": "fruitstore_auth_db",
    }

