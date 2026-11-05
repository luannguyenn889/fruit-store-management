import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "FruitStore Management API"
    API_V1_STR: str = "/api/v1"

    # Security / JWT
    SECRET_KEY: str = "fruitstore_super_secret_jwt_key_2026_safe_and_secure_random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = (
        "569426721711-6ub3hgomi74b201otif6cpe3oq53s5fj.apps.googleusercontent.com"
    )

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    # PostgreSQL Connection Strings (Database-per-Service)
    AUTH_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_auth_db"
    )
    CATALOG_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_catalog_db"
    )
    INVENTORY_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_inventory_db"
    )
    ORDER_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_order_db"
    )
    PAYMENT_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_payment_db"
    )
    REPORTING_DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fruitstore_reporting_db"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

