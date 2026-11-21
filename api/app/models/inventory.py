"""Stocks par produit et par magasin, et grand livre des mouvements (A.6 ; A-CAT-02, A-INV-01, A-INV-02).

Invariants :
- `inventory` : 0 <= reserved <= on_hand (contraintes CHECK de A.6).
- `stock_movements` est un grand livre en AJOUT SEULEMENT : un déclencheur SQL refuse tout
  UPDATE ou DELETE. Une erreur se corrige par un nouveau mouvement (p. ex. `adjustment`).
- Quantités SIGNÉES : positive = entrée, négative = sortie. Le signe est contrôlé par type.
- Réconciliation (L1) : `on_hand` = somme des quantités des mouvements PHYSIQUES du couple
  (produit, magasin). Les types `reservation` et `release` touchent `reserved`, pas `on_hand` :
  leur sémantique complète (avec les commandes) sera fixée au L2 avec l'ADR-001.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StockMovementType(enum.StrEnum):
    RECEIPT = "receipt"  # réception de marchandises (A-INV-02) — aussi utilisée par l'amorçage
    SALE = "sale"
    RESERVATION = "reservation"
    RELEASE = "release"
    ADJUSTMENT = "adjustment"  # perte, bris, correction (motif obligatoire, A-INV-03)
    RETURN = "return"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


# Types qui modifient le stock physique (`on_hand`).
PHYSICAL_MOVEMENT_TYPES = frozenset(
    {
        StockMovementType.RECEIPT,
        StockMovementType.SALE,
        StockMovementType.ADJUSTMENT,
        StockMovementType.RETURN,
        StockMovementType.TRANSFER_IN,
        StockMovementType.TRANSFER_OUT,
    }
)

# Règle de signe par type, vérifiée par une contrainte CHECK.
MOVEMENT_SIGN_RULE = (
    "(type IN ('receipt', 'return', 'transfer_in', 'reservation') AND quantity > 0)"
    " OR (type IN ('sale', 'transfer_out', 'release') AND quantity < 0)"
    " OR (type = 'adjustment' AND quantity <> 0)"
)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("on_hand >= 0", name="on_hand_non_negative"),
        CheckConstraint("reserved >= 0", name="reserved_non_negative"),
        CheckConstraint("reserved <= on_hand", name="reserved_le_on_hand"),
        CheckConstraint("reorder_threshold >= 0", name="reorder_threshold_non_negative"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Incrémentée à chaque changement : prépare le contrôle optimiste du L2 (ADR-001).
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        # Un mouvement vise toujours une ligne d'inventaire existante (DEC-DATA-02).
        ForeignKeyConstraint(
            ["product_id", "store_id"],
            ["inventory.product_id", "inventory.store_id"],
            name="fk_stock_movements_inventory",
            ondelete="RESTRICT",
        ),
        CheckConstraint(MOVEMENT_SIGN_RULE, name="quantity_sign_matches_type"),
        CheckConstraint(
            "type <> 'adjustment' OR (reason IS NOT NULL AND char_length(btrim(reason)) > 0)",
            name="adjustment_has_reason",
        ),
        Index("ix_stock_movements_product_store_created", "product_id", "store_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column()
    store_id: Mapped[uuid.UUID] = mapped_column()
    type: Mapped[StockMovementType] = mapped_column(
        Enum(
            StockMovementType,
            name="stock_movement_type",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda e: [x.value for x in e],
        )
    )
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    # Les utilisateurs ne sont jamais supprimés (anonymisation, A-PRV-03) : RESTRICT par défaut.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
