"""A-ORD-01, A-ORD-02, RA-A-07 — Panier côté serveur.

CA A-ORD-01 : le même panier est visible sur le web et le mobile pour un même compte.
A-ORD-02 : le panier valide la disponibilité dans le magasin choisi et signale les articles non
disponibles. A-ORD-03 / défi A-D2 : un prix envoyé par le client est ignoré (ici : refusé).
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models import Cart, CartItem, UserRole
from app.services import inventory_service
from tests.conftest import auth_header, error_code

CART = "/api/v1/cart"
ITEMS = "/api/v1/cart/items"


@pytest.fixture
def client_user(make_user):
    return make_user(UserRole.CLIENT)


@pytest.fixture
def headers(client_user):
    return auth_header(client_user)


@pytest.fixture
def stock(db):
    """Donne `quantity` unités d'un produit dans un magasin (mouvement `receipt`, grand livre)."""

    def _stock(product, store, quantity: int) -> None:
        inventory_service.create_initial_stock(
            db,
            product_id=product.id,
            store_id=store.id,
            quantity=quantity,
            reorder_threshold=2,
            reason="test",
        )
        db.commit()

    return _stock


def add(client, headers, product, quantity=1):
    return client.post(ITEMS, headers=headers, json={"product_id": str(product.id), "quantity": quantity})


# ---------------------------------------------------------------------------
# Lecture et ajout
# ---------------------------------------------------------------------------
def test_empty_cart_is_returned_without_being_created(client, db, headers, client_user):
    response = client.get(CART, headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "store_id": None,
        "store_name": None,
        "items": [],
        "item_count": 0,
        "subtotal_cents": 0,
        "has_unavailable_items": False,
    }
    assert db.scalar(select(func.count()).select_from(Cart)) == 0  # une lecture n'écrit rien (C3)


def test_add_item_uses_database_price(client, headers, make_product):
    drill = make_product("PERC-18V", price_cents=12999)
    body = add(client, headers, drill, 2).json()

    [line] = body["items"]
    assert line["sku"] == "PERC-18V"
    assert line["unit_price_cents"] == 12999
    assert line["quantity"] == 2
    assert line["line_total_cents"] == 25998
    assert body["subtotal_cents"] == 25998
    assert body["item_count"] == 2


def test_client_price_is_refused(client, headers, make_product):
    """Défi A-D2 : un prix falsifié n'est jamais pris en compte (champ refusé)."""
    drill = make_product("PERC-18V", price_cents=12999)
    response = client.post(
        ITEMS, headers=headers, json={"product_id": str(drill.id), "quantity": 1, "price_cents": 1}
    )
    assert response.status_code == 422
    assert client.get(CART, headers=headers).json()["items"] == []


def test_subtotal_follows_current_database_price(client, db, headers, make_product):
    drill = make_product("PERC-18V", price_cents=10000)
    add(client, headers, drill, 3)
    drill.price_cents = 9000
    db.commit()
    assert client.get(CART, headers=headers).json()["subtotal_cents"] == 27000


def test_adding_same_product_adds_quantities(client, headers, make_product):
    drill = make_product("PERC-18V")
    add(client, headers, drill, 2)
    body = add(client, headers, drill, 3).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


def test_quantity_limit_of_20_per_product(client, headers, make_product):
    drill = make_product("PERC-18V")
    assert add(client, headers, drill, 15).status_code == 200
    over = add(client, headers, drill, 6)
    assert over.status_code == 422
    assert error_code(over) == "quantity_limit"
    assert client.get(CART, headers=headers).json()["items"][0]["quantity"] == 15  # inchangé


@pytest.mark.parametrize("quantity", [0, -1, 21, "2", 2.5, None])
def test_invalid_quantities_are_refused(client, headers, make_product, quantity):
    drill = make_product("PERC-18V")
    response = client.post(ITEMS, headers=headers, json={"product_id": str(drill.id), "quantity": quantity})
    assert response.status_code == 422


def test_unknown_product_is_404(client, headers):
    response = client.post(
        ITEMS, headers=headers, json={"product_id": "00000000-0000-4000-8000-000000000000", "quantity": 1}
    )
    assert response.status_code == 404
    assert error_code(response) == "product_not_found"


def test_inactive_product_cannot_be_added(client, headers, make_product):
    old = make_product("VIEUX-001", is_active=False)
    response = add(client, headers, old)
    assert response.status_code == 422
    assert error_code(response) == "product_inactive"


# ---------------------------------------------------------------------------
# Modification et suppression
# ---------------------------------------------------------------------------
def test_update_quantity(client, headers, make_product):
    drill = make_product("PERC-18V", price_cents=1000)
    item_id = add(client, headers, drill, 2).json()["items"][0]["id"]

    body = client.patch(f"{ITEMS}/{item_id}", headers=headers, json={"quantity": 7}).json()
    assert body["items"][0]["quantity"] == 7
    assert body["subtotal_cents"] == 7000


@pytest.mark.parametrize("quantity", [0, 21])
def test_update_quantity_out_of_range(client, headers, make_product, quantity):
    item_id = add(client, headers, make_product("PERC-18V")).json()["items"][0]["id"]
    assert client.patch(f"{ITEMS}/{item_id}", headers=headers, json={"quantity": quantity}).status_code == 422


def test_remove_item(client, headers, make_product):
    drill = make_product("PERC-18V")
    saw = make_product("SCIE-001")
    add(client, headers, drill)
    item_id = add(client, headers, saw).json()["items"][1]["id"]

    body = client.delete(f"{ITEMS}/{item_id}", headers=headers).json()
    assert [line["sku"] for line in body["items"]] == ["PERC-18V"]


def test_unknown_item_is_404(client, headers):
    missing = "00000000-0000-4000-8000-000000000000"
    for response in (
        client.patch(f"{ITEMS}/{missing}", headers=headers, json={"quantity": 1}),
        client.delete(f"{ITEMS}/{missing}", headers=headers),
    ):
        assert response.status_code == 404
        assert error_code(response) == "cart_item_not_found"


def test_cannot_touch_another_clients_item(client, make_user, make_product):
    """IDOR (défi A-D4) : l'article de B répond 404 pour A, comme s'il n'existait pas."""
    alice, bob = auth_header(make_user()), auth_header(make_user())
    bob_item = add(client, bob, make_product("PERC-18V"), 2).json()["items"][0]["id"]

    assert client.patch(f"{ITEMS}/{bob_item}", headers=alice, json={"quantity": 20}).status_code == 404
    assert client.delete(f"{ITEMS}/{bob_item}", headers=alice).status_code == 404
    assert client.get(CART, headers=bob).json()["items"][0]["quantity"] == 2  # intact


# ---------------------------------------------------------------------------
# Magasin et disponibilité (A-ORD-02)
# ---------------------------------------------------------------------------
def test_items_unavailable_until_a_store_is_chosen(client, headers, make_product):
    body = add(client, headers, make_product("PERC-18V")).json()
    assert body["items"][0]["is_available"] is False
    assert body["items"][0]["unavailable_reason"] == "no_store_selected"
    assert body["has_unavailable_items"] is True


def test_availability_in_chosen_store(client, headers, make_product, make_store, stock):
    drill, saw, glue = make_product("PERC-18V"), make_product("SCIE-001"), make_product("COLLE-001")
    store = make_store("Saint-Jérôme")
    stock(drill, store, 10)
    stock(saw, store, 1)
    # `glue` : aucune ligne d'inventaire dans ce magasin

    add(client, headers, drill, 3)
    add(client, headers, saw, 2)
    add(client, headers, glue, 1)
    body = client.put(CART, headers=headers, json={"store_id": str(store.id)}).json()

    assert body["store_name"] == "Saint-Jérôme"
    reasons = {line["sku"]: line["unavailable_reason"] for line in body["items"]}
    assert reasons == {"PERC-18V": None, "SCIE-001": "insufficient_stock", "COLLE-001": "insufficient_stock"}
    assert body["has_unavailable_items"] is True
    assert all("on_hand" not in line and "available" not in line for line in body["items"])  # aucune quantité


def test_reserved_units_are_not_available(client, db, headers, make_product, make_store, stock):
    """RA-A-02 : disponible = en main − réservé."""
    from app.models import Inventory

    drill, store = make_product("PERC-18V"), make_store()
    stock(drill, store, 5)
    db.get(Inventory, (drill.id, store.id)).reserved = 4
    db.commit()

    add(client, headers, drill, 2)
    body = client.put(CART, headers=headers, json={"store_id": str(store.id)}).json()
    assert body["items"][0]["unavailable_reason"] == "insufficient_stock"


def test_unknown_store_is_404(client, headers):
    response = client.put(CART, headers=headers, json={"store_id": "00000000-0000-4000-8000-000000000000"})
    assert response.status_code == 404
    assert error_code(response) == "store_not_found"


def test_product_deactivated_after_adding_is_flagged_and_excluded(client, db, headers, make_product):
    drill, saw = make_product("PERC-18V", price_cents=1000), make_product("SCIE-001", price_cents=500)
    add(client, headers, drill, 2)
    add(client, headers, saw, 1)
    drill.is_active = False
    db.commit()

    body = client.get(CART, headers=headers).json()
    reasons = {line["sku"]: line["unavailable_reason"] for line in body["items"]}
    assert reasons["PERC-18V"] == "product_inactive"  # toujours visible (C5)
    assert body["subtotal_cents"] == 500  # exclu du sous-total


# ---------------------------------------------------------------------------
# Partage web / mobile, accès et concurrence
# ---------------------------------------------------------------------------
def test_same_cart_on_web_and_mobile(client, make_user, make_product):
    """CA A-ORD-01 : deux sessions du même compte (web et mobile) voient le même panier."""
    user = make_user()
    web, mobile = auth_header(user), auth_header(user)  # deux jetons distincts, même compte
    add(client, web, make_product("PERC-18V"), 2)
    assert client.get(CART, headers=mobile).json()["items"][0]["quantity"] == 2


def test_requires_authentication(client):
    assert client.get(CART).status_code == 401
    assert client.post(ITEMS, json={}).status_code == 401


@pytest.mark.parametrize("role", [UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN])
def test_staff_has_no_cart(client, make_user, role):
    response = client.get(CART, headers=auth_header(make_user(role)))
    assert response.status_code == 403
    assert error_code(response) == "insufficient_role"


def test_concurrent_additions_respect_the_limit(db, client_user, make_product):
    """C7 : deux ajouts simultanés (web et mobile) de 15 unités → un seul réussit, aucun doublon."""
    drill = make_product("PERC-18V")
    headers = auth_header(client_user)

    def add_15(_):
        with TestClient(app, base_url="https://testserver") as c:
            return c.post(
                ITEMS, headers=headers, json={"product_id": str(drill.id), "quantity": 15}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(add_15, range(2)))

    assert statuses == [200, 422]
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Cart)) == 1
    assert db.scalars(select(CartItem.quantity)).all() == [15]
