"""
Module: app.core.config (API Gateway)
Nhiệm vụ: Nạp cấu hình môi trường cho API Gateway (cổng 8000), bao gồm khóa xác thực JWT,
          khóa giao tiếp nội bộ `INTERNAL_API_KEY`, danh sách CORS origins và URL của
          các microservice đích (`auth-service`, `catalog-service`).
"""

import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Lớp cấu hình cho API Gateway."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SERVICE_NAME: str = "FruitStore API Gateway"
    PORT: int = 8000

    # Cấu hình xác thực JWT
    SECRET_KEY: str = "fruitstore_super_secret_jwt_key_2026_safe_and_secure_random"
    ALGORITHM: str = "HS256"

    # Khóa nội bộ xác thực giữa Gateway và các Service
    INTERNAL_API_KEY: str = "fruitstore_internal_gateway_key_2026"

    # Địa chỉ các downstream services
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    CATALOG_SERVICE_URL: str = "http://localhost:8002"

    # Cấu hình CORS cho Angular Frontend
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [item.strip() for item in v.split(",")]
        if isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = GatewaySettings()

