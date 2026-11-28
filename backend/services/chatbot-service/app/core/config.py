"""
Module: app.core.config (Chatbot Service)
Nhiệm vụ: Quản lý cấu hình môi trường (.env) cho Chatbot Service (:8007):
          - Chuỗi kết nối `DATABASE_URL` tới `fruitstore_chatbot_db` (role `chatbot_user`).
          - Khóa nội bộ `INTERNAL_API_KEY` từ API Gateway và khi gọi sang Catalog/Inventory.
          - Khóa `GEMINI_API_KEY` và tên model Gemini (`gemini-2.5-flash`).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatbotSettings(BaseSettings):
    """Lớp cấu hình trung tâm của Chatbot Service."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SERVICE_NAME: str = "FruitStore Chatbot Service"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8007

    DATABASE_URL: str = (
        "postgresql+asyncpg://chatbot_user:CHANGE_ME_chatbot@localhost:5432/fruitstore_chatbot_db"
    )
    INTERNAL_API_KEY: str = "fruitstore_internal_gateway_key_2026"

    CATALOG_SERVICE_URL: str = "http://localhost:8002"
    INVENTORY_SERVICE_URL: str = "http://localhost:8003"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.1-flash-lite,gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = ChatbotSettings()
