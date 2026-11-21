"""Stocks : enregistrement des mouvements, statut de disponibilité et réconciliation (A-INV-01, A-CAT-02).

Règle unique d'écriture : un changement de `on_hand` passe TOUJOURS par `record_movement`, qui
verrouille la ligne d'inventaire (SELECT … FOR UPDATE, ADR-001), ajoute le mouvement au grand livre
et met à jour la quantité dans la MÊME transaction. Les contraintes SQL refusent un stock négatif.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.models import PHYSICAL_MOVEMENT_TYPES, Inventory, StockMovement, StockMovementType

IN_STOCK = "in_stock"
LOW_STOCK = "low_stock"
OUT_OF_STOCK = "out_of_stock"


def availability_status(on_hand: int, reserved: int, reorder_threshold: int) -> str:
    """Statut public calculé à partir du stock réel (A-CAT-02), jamais stocké comme texte.

    Rupture : disponible <= 0 · Stock faible : disponible <= seuil · En stock : au-dessus du seuil.
    """
    available = on_hand - reserved
    if available <= 0:
        return OUT_OF_STOCK
    if available <= reorder_threshold:
        return LOW_STOCK
    return IN_STOCK


def ensure_inventory(
    db: Session, product_id: uuid.UUID, store_id: uuid.UUID, *, reorder_threshold: int = 0
) -> Inventory:
    """Crée la ligne d'inventaire (stock 0) si elle n'existe pas encore, sans valider la transaction."""
    inventory = db.get(Inventory, (product_id, store_id))
    if inventory is None:
        inventory = Inventory(
            product_id=product_id,
            store_id=store_id,
            on_hand=0,
            reserved=0,
            reorder_threshold=reorder_threshold,
        )
        db.add(inventory)
        db.flush()
    return inventory


def record_movement(
    db: Session,
    *,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
    type: StockMovementType,
    quantity: int,
    reason: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> StockMovement:
    """Ajoute un mouvement PHYSIQUE et applique son effet sur `on_hand`, sous verrou de ligne.

    Ne valide pas la transaction : l'appelant fait `db.commit()` (ou annule tout en cas d'erreur).
    """
    if type not in PHYSICAL_MOVEMENT_TYPES:
        # reservation / release : sémantique liée aux commandes, prévue au L2 (ADR-001).
        raise ValidationFailed(
            "movement_type_not_supported", "Ce type de mouvement n'est pas encore pris en charge."
        )
    inventory = db.execute(
        select(Inventory)
        .where(Inventory.product_id == product_id, Inventory.store_id == store_id)
        .with_for_update()
    ).scalar_one_or_none()
    if inventory is None:
        raise ValidationFailed(
            "inventory_not_found", "Aucune ligne d'inventaire pour ce produit et ce magasin."
        )
    if inventory.on_hand + quantity < inventory.reserved:
        raise ValidationFailed("insufficient_stock", "Stock insuffisant pour ce mouvement.")
    movement = StockMovement(
        product_id=product_id,
        store_id=store_id,
        type=type,
        quantity=quantity,
        reason=reason,
        actor_id=actor_id,
    )
    db.add(movement)
    inventory.on_hand += quantity
    inventory.version += 1
    db.flush()
    return movement


def create_initial_stock(
    db: Session,
    *,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
    quantity: int,
    reorder_threshold: int,
    reason: str,
) -> Inventory:
    """Crée une NOUVELLE ligne d'inventaire et son stock de départ par un mouvement `receipt`.

    Chemin d'écriture en lot (amorçage) : la ligne n'existe pas encore, donc aucun verrou n'est
    nécessaire; `on_hand` et le grand livre sont écrits dans la même transaction, et l'invariant
    `on_hand` = somme des mouvements est respecté dès la création. Ne valide pas la transaction.
    """
    inventory = Inventory(
        product_id=product_id,
        store_id=store_id,
        on_hand=quantity,
        reserved=0,
        reorder_threshold=reorder_threshold,
        version=1,
    )
    db.add(inventory)
    if quantity > 0:
        db.add(
            StockMovement(
                product_id=product_id,
                store_id=store_id,
                type=StockMovementType.RECEIPT,
                quantity=quantity,
                reason=reason,
            )
        )
    return inventory


@dataclass(frozen=True)
class Discrepancy:
    product_id: uuid.UUID
    store_id: uuid.UUID
    on_hand: int
    ledger_total: int


def find_discrepancies(db: Session) -> list[Discrepancy]:
    """Réconciliation : lignes où `on_hand` diffère de la somme des mouvements physiques (A-INV-01)."""
    ledger = (
        select(
            StockMovement.product_id,
            StockMovement.store_id,
            func.sum(StockMovement.quantity).label("total"),
        )
        .where(StockMovement.type.in_(list(PHYSICAL_MOVEMENT_TYPES)))
        .group_by(StockMovement.product_id, StockMovement.store_id)
        .subquery()
    )
    rows = db.execute(
        select(Inventory.product_id, Inventory.store_id, Inventory.on_hand, func.coalesce(ledger.c.total, 0))
        .outerjoin(
            ledger,
            (ledger.c.product_id == Inventory.product_id) & (ledger.c.store_id == Inventory.store_id),
        )
        .where(Inventory.on_hand != func.coalesce(ledger.c.total, 0))
    ).all()
    return [Discrepancy(*row) for row in rows]
