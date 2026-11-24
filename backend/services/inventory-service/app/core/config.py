"""
Module: app.core.config (Inventory Service)
Nhiệm vụ: Quản lý cấu hình môi trường (.env) cho Inventory Service:
          - Cổng dịch vụ độc lập (`8003`).
          - Chuỗi kết nối `DATABASE_URL` tới `fruitstore_inventory_db` (role `inventory_user`, NFR-S08).
          - Khóa xác thực nội bộ `INTERNAL_API_KEY` từ API Gateway và URL `CATALOG_SERVICE_URL`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class InventorySettings(BaseSettings):
    """Lớp cấu hình trung tâm của Inventory Service."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SERVICE_NAME: str = "FruitStore Inventory Service"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8003

    # Chuỗi kết nối riêng biệt tới database của Inventory Service (NFR-S08)
    DATABASE_URL: str = (
        "postgresql+asyncpg://inventory_user:CHANGE_ME_inventory@localhost:5432/fruitstore_inventory_db"
    )

    # Khóa nội bộ kiểm tra request đến từ API Gateway
    INTERNAL_API_KEY: str = "fruitstore_internal_gateway_key_2026"

    # Địa chỉ Catalog Service để xác thực product_id qua REST (SOA, không JOIN chéo DB)
    CATALOG_SERVICE_URL: str = "http://localhost:8002"

    # Tham số nghiệp vụ mặc định theo SRS (FR-C06, BR-06)
    NEAR_EXPIRY_DAYS: int = 3
    RESERVATION_TTL_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = InventorySettings()
