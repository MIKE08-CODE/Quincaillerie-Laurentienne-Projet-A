"""Registre des modèles SQLAlchemy.

Chaque nouveau modèle doit être importé ici : alembic/env.py importe ce paquet, et Alembic
ne détecte que les tables dont le modèle a été importé.
"""

from app.models.auth_token import OneTimeToken, OneTimeTokenPurpose, RefreshToken
from app.models.catalog import Brand, Category, Product, ProductImage
from app.models.consent import Consent, ConsentType
from app.models.inventory import PHYSICAL_MOVEMENT_TYPES, Inventory, StockMovement, StockMovementType
from app.models.order import Cart, CartItem, Order, OrderItem, OrderStatus, OrderStatusHistory, PaymentEvent
from app.models.store import StaffAssignment, Store
from app.models.user import STAFF_ROLES, User, UserRole

__all__ = [
    "PHYSICAL_MOVEMENT_TYPES",
    "STAFF_ROLES",
    "Brand",
    "Cart",
    "CartItem",
    "Category",
    "Consent",
    "ConsentType",
    "Inventory",
    "OneTimeToken",
    "OneTimeTokenPurpose",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderStatusHistory",
    "PaymentEvent",
    "Product",
    "ProductImage",
    "RefreshToken",
    "StaffAssignment",
    "StockMovement",
    "StockMovementType",
    "Store",
    "User",
    "UserRole",
]
