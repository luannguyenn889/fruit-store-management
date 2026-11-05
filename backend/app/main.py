import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.sessions import auth_engine, AuthSessionLocal, Base
from app.models.user import User, Role  # noqa: F401
from app.routers.auth import router as auth_router
from app.services.auth_service import AuthService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fruitstore")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và tắt của ứng dụng"""
    logger.info("Đang khởi động FruitStore Management Backend...")
    try:
        # Tự động tạo bảng trong Auth DB nếu chưa có
        Base.metadata.create_all(bind=auth_engine)
        logger.info("Khởi tạo cấu trúc bảng Auth DB thành công.")

        # Khởi tạo roles và tài khoản admin mặc định
        with AuthSessionLocal() as db:
            AuthService.init_roles_and_admin(db)
            logger.info(
                "Đã kiểm tra/khởi tạo Roles mặc định và tài khoản Admin: admin@fruitstore.com"
            )
    except Exception as e:
        logger.warning(
            f"Chưa thể kết nối tới PostgreSQL (kiểm tra lại mật khẩu/DB đã tạo chưa): {e}"
        )

    yield

    logger.info("Đang dừng ứng dụng FruitStore Management Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Hệ thống Quản lý Cửa hàng Trái cây (FruitStore Management System) - SOA Architecture",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Cấu hình CORS cho phép Angular Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router nghiệp vụ
app.include_router(auth_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

