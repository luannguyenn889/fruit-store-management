"""
Module: app.core.config (Catalog Service)
Nhiệm vụ: Quản lý cấu hình môi trường (.env) cho Catalog Service:
          - Cổng dịch vụ độc lập (`8002`).
          - Chuỗi kết nối `DATABASE_URL` tới `fruitstore_catalog_db` (role `catalog_user`).
          - Khóa xác thực nội bộ `INTERNAL_API_KEY` từ API Gateway.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class CatalogSettings(BaseSettings):
    """Lớp cấu hình trung tâm của Catalog Service."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SERVICE_NAME: str = "FruitStore Catalog Service"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8002

    # Chuỗi kết nối riêng biệt tới database của Catalog Service (NFR-S08)
    DATABASE_URL: str = (
        "postgresql+asyncpg://catalog_user:CHANGE_ME_catalog@localhost:5432/fruitstore_catalog_db"
    )

    # Khóa nội bộ kiểm tra request đến từ API Gateway
    INTERNAL_API_KEY: str = "fruitstore_internal_gateway_key_2026"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = CatalogSettings()

