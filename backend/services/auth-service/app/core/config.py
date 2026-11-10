"""
Module: app.core.config
Nhiệm vụ: Quản lý và nạp toàn bộ cấu hình môi trường (.env) cho Auth Service
          như chuỗi kết nối `fruitstore_auth_db`, khóa ký JWT, thời hạn token (30 phút),
          khóa nội bộ `INTERNAL_API_KEY` và `GOOGLE_CLIENT_ID`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lớp cấu hình trung tâm của Auth Service sử dụng Pydantic Settings."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SERVICE_NAME: str = "FruitStore Auth Service"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8001

    # Chuỗi kết nối riêng biệt tới database của Auth Service (NFR-S08)
    DATABASE_URL: str = (
        "postgresql+asyncpg://auth_user:CHANGE_ME_auth@localhost:5432/fruitstore_auth_db"
    )

    # Cấu hình bảo mật JWT (SRS yêu cầu Access Token có thời hạn 15–30 phút)
    SECRET_KEY: str = "fruitstore_super_secret_jwt_key_2026_safe_and_secure_random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Khóa nội bộ dùng để xác thực các request được chuyển tiếp từ API Gateway
    INTERNAL_API_KEY: str = "fruitstore_internal_gateway_key_2026"

    # Google OAuth 2.0 Client ID dùng để xác thực chữ ký ID Token
    GOOGLE_CLIENT_ID: str = (
        "569426721711-6ub3hgomi74b201otif6cpe3oq53s5fj.apps.googleusercontent.com"
    )

    # Mật khẩu khởi tạo dữ liệu mẫu (chỉ dùng khi chạy script seed tường minh)
    SEED_ADMIN_PASSWORD: str = "Admin@123"
    SEED_MANAGER_PASSWORD: str = "Manager@123"
    SEED_STAFF_PASSWORD: str = "Staff@123"
    SEED_WAREHOUSE_PASSWORD: str = "Warehouse@123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

