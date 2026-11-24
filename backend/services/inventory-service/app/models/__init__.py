"""
Module: app.models (Inventory Service)
Nhiệm vụ: Export đầy đủ 7 ORM models để Alembic (`env.py`) tự động nhận diện vào `Base.metadata`.
"""

from app.models.inventory import (
    PurchaseItem,
    PurchaseOrder,
    Reservation,
    ReservationItem,
    StockLot,
    StockMovement,
    Supplier,
)

__all__ = [
    "Supplier",
    "PurchaseOrder",
    "PurchaseItem",
    "StockLot",
    "Reservation",
    "ReservationItem",
    "StockMovement",
]
