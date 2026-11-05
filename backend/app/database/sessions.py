from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# Base class cho toàn bộ ORM Models
Base = declarative_base()

# ==============================================================================
# ENGINES & SESSION MAKERS RIÊNG BIỆT CHO TỪNG DATABASE (SOA Database-per-Service)
# ==============================================================================

# 1. Auth Service Database
auth_engine = create_engine(
    settings.AUTH_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)

# 2. Catalog Service Database
catalog_engine = create_engine(
    settings.CATALOG_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
CatalogSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=catalog_engine
)

# 3. Inventory Service Database
inventory_engine = create_engine(
    settings.INVENTORY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
InventorySessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=inventory_engine
)

# 4. Order Service Database
order_engine = create_engine(
    settings.ORDER_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
OrderSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=order_engine)

# 5. Payment Service Database
payment_engine = create_engine(
    settings.PAYMENT_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
PaymentSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=payment_engine
)

# 6. Reporting Service Database
reporting_engine = create_engine(
    settings.REPORTING_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)
ReportingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=reporting_engine
)


# ==============================================================================
# FASTAPI DEPENDENCIES: Cung cấp session cho từng Router
# ==============================================================================

def get_auth_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_auth_db"""
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_catalog_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_catalog_db"""
    db = CatalogSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_inventory_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_inventory_db"""
    db = InventorySessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_order_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_order_db"""
    db = OrderSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_payment_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_payment_db"""
    db = PaymentSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_reporting_db() -> Generator[Session, None, None]:
    """Dependency cung cấp Session kết nối tới fruitstore_reporting_db"""
    db = ReportingSessionLocal()
    try:
        yield db
    finally:
        db.close()
