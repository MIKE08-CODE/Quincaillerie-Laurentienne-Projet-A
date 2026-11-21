"""Stocks : contraintes de `inventory`, grand livre `stock_movements` et invariants (A-INV-01, A-CAT-02)."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.models import Inventory, StockMovement, StockMovementType
from app.services import inventory_service
from app.services.inventory_service import IN_STOCK, LOW_STOCK, OUT_OF_STOCK, availability_status


@pytest.fixture
def stock(db: Session, make_product, make_store):
    """Un produit, un magasin et une ligne d'inventaire vide (seuil 5)."""
    product = make_product("STK-1")
    store = make_store()
    inventory = inventory_service.ensure_inventory(db, product.id, store.id, reorder_threshold=5)
    db.commit()
    return product, store, inventory


def _receive(db: Session, product, store, quantity: int, type=StockMovementType.RECEIPT, reason=None):
    movement = inventory_service.record_movement(
        db, product_id=product.id, store_id=store.id, type=type, quantity=quantity, reason=reason
    )
    db.commit()
    return movement


@pytest.mark.parametrize(
    ("on_hand", "reserved", "constraint"),
    [
        (-1, 0, "ck_inventory_on_hand_non_negative"),
        (5, -1, "ck_inventory_reserved_non_negative"),
        (3, 4, "ck_inventory_reserved_le_on_hand"),
    ],
)
def test_inventory_check_constraints(db: Session, stock, on_hand, reserved, constraint):
    _, _, inventory = stock
    inventory.on_hand, inventory.reserved = on_hand, reserved
    with pytest.raises(IntegrityError) as excinfo:
        db.commit()
    db.rollback()
    assert excinfo.value.orig.diag.constraint_name == constraint


def test_record_movement_updates_on_hand_and_version(db: Session, stock):
    product, store, inventory = stock
    _receive(db, product, store, 12)
    _receive(db, product, store, -2, StockMovementType.ADJUSTMENT, reason="Bris en magasin")
    db.refresh(inventory)
    assert (inventory.on_hand, inventory.version) == (10, 3)
    assert inventory_service.find_discrepancies(db) == []


def test_movement_cannot_make_stock_negative(db: Session, stock):
    product, store, _ = stock
    _receive(db, product, store, 3)
    with pytest.raises(ValidationFailed) as excinfo:
        _receive(db, product, store, -5, StockMovementType.SALE)
    db.rollback()
    assert excinfo.value.code == "insufficient_stock"
    assert db.scalar(select(Inventory.on_hand)) == 3


def test_reservation_types_are_not_supported_before_l2(db: Session, stock):
    product, store, _ = stock
    with pytest.raises(ValidationFailed):
        _receive(db, product, store, 1, StockMovementType.RESERVATION)


@pytest.mark.parametrize(
    ("type", "quantity"),
    [("receipt", -1), ("receipt", 0), ("sale", 2), ("transfer_out", 1), ("release", 1), ("reservation", -1)],
)
def test_quantity_sign_must_match_type(db: Session, stock, type, quantity):
    product, store, _ = stock
    with pytest.raises(IntegrityError) as excinfo:
        db.execute(
            text(
                "INSERT INTO stock_movements (id, product_id, store_id, type, quantity) "
                "VALUES (gen_random_uuid(), :p, :s, :t, :q)"
            ),
            {"p": product.id, "s": store.id, "t": type, "q": quantity},
        )
    db.rollback()
    assert excinfo.value.orig.diag.constraint_name == "ck_stock_movements_quantity_sign_matches_type"


def test_adjustment_requires_a_reason(db: Session, stock):
    product, store, _ = stock
    db.add(
        StockMovement(
            product_id=product.id, store_id=store.id, type=StockMovementType.ADJUSTMENT, quantity=-1
        )
    )
    with pytest.raises(IntegrityError) as excinfo:
        db.commit()
    db.rollback()
    assert excinfo.value.orig.diag.constraint_name == "ck_stock_movements_adjustment_has_reason"


def test_unknown_movement_type_is_refused(db: Session, stock):
    product, store, _ = stock
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO stock_movements (id, product_id, store_id, type, quantity) "
                "VALUES (gen_random_uuid(), :p, :s, 'gift', 1)"
            ),
            {"p": product.id, "s": store.id},
        )
    db.rollback()


def test_movement_requires_an_existing_inventory_row(db: Session, make_product, make_store):
    product, store = make_product("NOINV"), make_store()
    db.add(
        StockMovement(product_id=product.id, store_id=store.id, type=StockMovementType.RECEIPT, quantity=1)
    )
    with pytest.raises(IntegrityError) as excinfo:
        db.commit()
    db.rollback()
    assert excinfo.value.orig.diag.constraint_name == "fk_stock_movements_inventory"


@pytest.mark.parametrize(
    "statement", ["UPDATE stock_movements SET quantity = 99", "DELETE FROM stock_movements"]
)
def test_stock_movements_are_append_only(db: Session, stock, statement):
    product, store, _ = stock
    _receive(db, product, store, 4)
    with pytest.raises(DBAPIError) as excinfo:
        db.execute(text(statement))
    db.rollback()
    assert "append-only" in str(excinfo.value.orig)
    assert db.scalar(select(StockMovement.quantity)) == 4


def test_reconciliation_detects_a_manual_change_of_on_hand(db: Session, stock):
    product, store, inventory = stock
    _receive(db, product, store, 7)
    inventory.on_hand = 9  # modification hors du grand livre
    db.commit()
    [discrepancy] = inventory_service.find_discrepancies(db)
    assert (discrepancy.on_hand, discrepancy.ledger_total) == (9, 7)


@pytest.mark.parametrize(
    ("on_hand", "reserved", "threshold", "expected"),
    [
        (0, 0, 5, OUT_OF_STOCK),
        (3, 3, 5, OUT_OF_STOCK),  # tout est réservé
        (1, 0, 5, LOW_STOCK),
        (5, 0, 5, LOW_STOCK),  # égal au seuil : stock faible
        (6, 0, 5, IN_STOCK),
        (10, 5, 5, LOW_STOCK),  # disponible = 5
        (1, 0, 0, IN_STOCK),
    ],
)
def test_availability_status_rule(on_hand, reserved, threshold, expected):
    assert availability_status(on_hand, reserved, threshold) == expected
