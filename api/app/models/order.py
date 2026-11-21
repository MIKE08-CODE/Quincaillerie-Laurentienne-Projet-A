"""Paniers, commandes et paiements (A.6 ; A-ORD-01 à 07, A-PCK-01 à 03).

Ces tables sont créées dès le L1 parce que A.11 exige « des migrations pour toutes les entités Must ».
AUCUNE route de panier, de commande ou de paiement n'existe au L1 : elles arrivent au L2.

- Un panier par client (UNIQUE user_id), avec le magasin de cueillette choisi (A-ORD-02).
- Montants en cents entiers; total = sous-total − remise + TPS + TVQ (contrôlé en SQL).
- `order_items` conserve un instantané du nom et du prix au moment de la commande.
- `payment_events.stripe_event_id` est la clé primaire : un webhook rejoué ne peut pas être
  enregistré deux fois (idempotence, A-ORD-06).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MAX_ITEM_QUANTITY = 20  # RA-A-07 : quantité de 1 à 20 par article


class OrderStatus(enum.StrEnum):
    """Machine à états d'A-ORD-07 (transitions appliquées par le service au L2)."""

    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


def _order_status_enum(name: str) -> Enum:
    return Enum(
        OrderStatus,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [x.value for x in e],
    )


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id"),
        CheckConstraint(f"quantity BETWEEN 1 AND {MAX_ITEM_QUANTITY}", name="quantity_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "subtotal_cents >= 0 AND discount_cents >= 0 AND gst_cents >= 0 AND qst_cents >= 0",
            name="amounts_non_negative",
        ),
        CheckConstraint("discount_cents <= subtotal_cents", name="discount_le_subtotal"),
        CheckConstraint(
            "total_cents = subtotal_cents - discount_cents + gst_cents + qst_cents", name="total_consistent"
        ),
        Index("ix_orders_store_status", "store_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    number: Mapped[str] = mapped_column(String(20), unique=True)  # numéro lisible
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"))
    status: Mapped[OrderStatus] = mapped_column(
        _order_status_enum("order_status"), default=OrderStatus.PENDING_PAYMENT
    )
    subtotal_cents: Mapped[int] = mapped_column(BigInteger)
    discount_cents: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    gst_cents: Mapped[int] = mapped_column(BigInteger)
    qst_cents: Mapped[int] = mapped_column(BigInteger)
    total_cents: Mapped[int] = mapped_column(BigInteger)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    pickup_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)  # empreinte seulement
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(f"quantity BETWEEN 1 AND {MAX_ITEM_QUANTITY}", name="quantity_range"),
        CheckConstraint("unit_price_cents >= 0", name="unit_price_non_negative"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_cents: Mapped[int] = mapped_column(BigInteger)
    product_name_snapshot: Mapped[str] = mapped_column(String(200))


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[OrderStatus | None] = mapped_column(_order_status_enum("order_status_from"))
    to_status: Mapped[OrderStatus] = mapped_column(_order_status_enum("order_status_to"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    stripe_event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
