"""Tables Must transactionnelles créées au L1 sans route (A.6, A-ORD-01 à 07).

Ces tests vérifient seulement les contraintes SQL : la logique de panier, de commande et de paiement
arrive au L2.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentEvent,
    StockMovement,
    StockMovementType,
    UserRole,
)
from app.services import inventory_service


@pytest.fixture
def context(db: Session, make_user, make_store, make_product):
    return make_user(UserRole.CLIENT), make_store(), make_product("ORD-1")


def _order(user, store, **overrides) -> Order:
    values = {
        "number": f"QL-{uuid.uuid4().hex[:8].upper()}",
        "user_id": user.id,
        "store_id": store.id,
        "subtotal_cents": 10000,
        "discount_cents": 0,
        "gst_cents": 500,
        "qst_cents": 998,
        "total_cents": 11498,
    } | overrides
    return Order(**values)


def _constraint_violated(db: Session, *objects) -> str:
    db.add_all(objects)
    with pytest.raises(IntegrityError) as excinfo:
        db.commit()
    db.rollback()
    return excinfo.value.orig.diag.constraint_name


@pytest.mark.parametrize("quantity", [0, 21])
def test_cart_item_quantity_between_1_and_20(db: Session, context, quantity):
    user, store, product = context
    cart = Cart(user_id=user.id, store_id=store.id)
    db.add(cart)
    db.commit()
    item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
    assert _constraint_violated(db, item) == "ck_cart_items_quantity_range"


def test_one_cart_per_user_and_one_line_per_product(db: Session, context):
    user, store, product = context
    cart = Cart(user_id=user.id)
    db.add(cart)
    db.flush()
    db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
    db.commit()
    assert _constraint_violated(db, CartItem(cart_id=cart.id, product_id=product.id, quantity=2)) == (
        "uq_cart_items_cart_id"
    )
    assert _constraint_violated(db, Cart(user_id=user.id)) == "uq_carts_user_id"


def test_valid_order_with_items_and_history(db: Session, context):
    user, store, product = context
    order = _order(user, store)
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=2,
            unit_price_cents=5000,
            product_name_snapshot=product.name_fr,
        )
    )
    db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.PENDING_PAYMENT))
    db.commit()
    assert order.status == OrderStatus.PENDING_PAYMENT


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"total_cents": 1}, "ck_orders_total_consistent"),
        ({"gst_cents": -1, "total_cents": 10997}, "ck_orders_amounts_non_negative"),
        ({"discount_cents": 10001, "total_cents": 1497}, "ck_orders_discount_le_subtotal"),
        ({"status": "shipped"}, "ck_orders_order_status"),
    ],
)
def test_order_constraints(db: Session, context, overrides, constraint):
    user, store, _ = context
    assert _constraint_violated(db, _order(user, store, **overrides)) == constraint


def test_order_number_is_unique(db: Session, context):
    user, store, _ = context
    db.add(_order(user, store, number="QL-000001"))
    db.commit()
    assert _constraint_violated(db, _order(user, store, number="QL-000001")) == "uq_orders_number"


def test_payment_event_cannot_be_recorded_twice(db: Session):
    db.add(PaymentEvent(stripe_event_id="evt_test_1", type="payment_intent.succeeded", payload={}))
    db.commit()
    duplicate = PaymentEvent(stripe_event_id="evt_test_1", type="payment_intent.succeeded", payload={})
    assert _constraint_violated(db, duplicate) == "pk_payment_events"


def test_stock_movement_order_must_exist(db: Session, context):
    _, store, product = context
    inventory_service.ensure_inventory(db, product.id, store.id)
    db.commit()
    movement = StockMovement(
        product_id=product.id,
        store_id=store.id,
        type=StockMovementType.RECEIPT,
        quantity=1,
        order_id=uuid.uuid4(),
    )
    assert _constraint_violated(db, movement) == "fk_stock_movements_order_id_orders"
