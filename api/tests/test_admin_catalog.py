"""Administration du catalogue (A-ADM-01) : rôles, CRUD, PATCH, désactivation, erreurs 401/403/404/409/422."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Brand, Category, Product, UserRole
from tests.conftest import auth_header, error_code

API = "/api/v1/admin"
ANY_ID = "00000000-0000-4000-8000-000000000000"

# Toutes les routes d'administration : chacune est testée pour chaque rôle (CA d'A-AUTH-05).
ADMIN_ROUTES = [
    ("GET", "/products"),
    ("POST", "/products"),
    ("GET", f"/products/{ANY_ID}"),
    ("PATCH", f"/products/{ANY_ID}"),
    ("DELETE", f"/products/{ANY_ID}"),
    ("POST", f"/products/{ANY_ID}/images"),
    ("POST", f"/products/{ANY_ID}/images/upload"),
    ("DELETE", f"/products/{ANY_ID}/images/{ANY_ID}"),
    ("GET", "/categories"),
    ("POST", "/categories"),
    ("PATCH", f"/categories/{ANY_ID}"),
    ("DELETE", f"/categories/{ANY_ID}"),
    ("GET", "/brands"),
    ("POST", "/brands"),
    ("PATCH", f"/brands/{ANY_ID}"),
    ("DELETE", f"/brands/{ANY_ID}"),
]


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_admin_routes_require_authentication(client, method, path):
    response = client.request(method, f"{API}{path}", json={})
    assert response.status_code == 401


@pytest.mark.parametrize("role", [UserRole.CLIENT, UserRole.CLERK, UserRole.MANAGER])
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_admin_routes_are_forbidden_to_other_roles(client, make_user, make_store, role, method, path):
    stores = [make_store()] if role in (UserRole.CLERK, UserRole.MANAGER) else []
    headers = auth_header(make_user(role, stores=stores), mfa=True)
    response = client.request(method, f"{API}{path}", json={}, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_admin_without_mfa_is_forbidden(client, make_user, method, path):
    headers = auth_header(make_user(UserRole.ADMIN), mfa=False)
    response = client.request(method, f"{API}{path}", json={}, headers=headers)
    assert response.status_code == 403 and error_code(response) == "mfa_required"


@pytest.mark.parametrize(("method", "path"), [r for r in ADMIN_ROUTES if r[0] == "GET"])
def test_admin_can_read(client, admin_headers, method, path):
    expected = 404 if ANY_ID in path else 200
    assert client.request(method, f"{API}{path}", headers=admin_headers).status_code == expected


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------
@pytest.fixture
def references(make_brand, make_category):
    return make_brand("Laurentide Pro", "laurentide-pro"), make_category("perceuses")


def _payload(brand: Brand, category: Category, **overrides) -> dict:
    return {
        "sku": "perc-18v-001",
        "name_fr": "  Perceuse sans fil 18 V ",
        "name_en": "18 V cordless drill",
        "description_fr": "Perceuse compacte.",
        "brand_id": str(brand.id),
        "category_id": str(category.id),
        "price_cents": 8999,
        "specs": {"tension_v": 18, "batteries": 2, "couleurs": ["jaune", "noir"]},
    } | overrides


def test_create_product(client, admin_headers, references):
    brand, category = references
    response = client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["sku"] == "PERC-18V-001"  # normalisé en majuscules
    assert body["name_fr"] == "Perceuse sans fil 18 V"  # espaces retirés
    assert body["brand"] == "Laurentide Pro" and body["brand_id"] == str(brand.id)
    assert body["is_active"] is True and body["description_en"] is None
    assert body["images"] == [] and body["availability"] == []
    # visible publiquement
    assert client.get(f"/api/v1/products/{body['id']}").status_code == 200


def test_duplicate_sku_is_409(client, admin_headers, references):
    brand, category = references
    client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers)
    response = client.post(
        f"{API}/products", json=_payload(brand, category, sku="PERC-18V-001"), headers=admin_headers
    )
    assert response.status_code == 409 and error_code(response) == "sku_taken"


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_cents": -1},
        {"price_cents": 12.5},
        {"price_cents": "8999"},
        {"sku": ""},
        {"sku": "AVEC ESPACE"},
        {"name_fr": "   "},
        {"name_en": "x" * 201},
        {"role": "admin"},  # champ inconnu refusé
        {"specs": "texte"},
        {"specs": {f"k{i}": i for i in range(51)}},
        {"specs": {"x": {"imbrique": True}}},
    ],
)
def test_invalid_product_is_422(client, admin_headers, references, overrides):
    brand, category = references
    response = client.post(
        f"{API}/products", json=_payload(brand, category, **overrides), headers=admin_headers
    )
    assert response.status_code == 422, overrides


def test_unknown_or_inactive_references(client, admin_headers, references, make_brand):
    brand, category = references
    unknown = client.post(
        f"{API}/products", json=_payload(brand, category, brand_id=str(uuid.uuid4())), headers=admin_headers
    )
    assert unknown.status_code == 404 and error_code(unknown) == "brand_not_found"
    no_cat = client.post(
        f"{API}/products",
        json=_payload(brand, category, category_id=str(uuid.uuid4())),
        headers=admin_headers,
    )
    assert no_cat.status_code == 404 and error_code(no_cat) == "category_not_found"
    inactive = make_brand("Ancienne", "ancienne", is_active=False)
    response = client.post(
        f"{API}/products", json=_payload(brand, category, brand_id=str(inactive.id)), headers=admin_headers
    )
    assert response.status_code == 422 and error_code(response) == "brand_inactive"


def test_patch_updates_only_sent_fields(client, admin_headers, references):
    brand, category = references
    created = client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers).json()
    response = client.patch(
        f"{API}/products/{created['id']}",
        json={"price_cents": 7999, "description_fr": None, "name_en": "Cordless drill"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["price_cents"], body["description_fr"], body["name_en"]) == (7999, None, "Cordless drill")
    assert body["name_fr"] == created["name_fr"] and body["specs"] == created["specs"]  # inchangés
    assert body["updated_at"] >= created["updated_at"]


@pytest.mark.parametrize("field", ["sku", "name_fr", "name_en", "price_cents", "specs", "is_active"])
def test_patch_refuses_null_on_required_fields(client, admin_headers, references, field):
    brand, category = references
    created = client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers).json()
    response = client.patch(f"{API}/products/{created['id']}", json={field: None}, headers=admin_headers)
    assert response.status_code == 422


def test_patch_sku_conflict_and_unknown_product(client, admin_headers, references, make_product):
    brand, category = references
    make_product("AUTRE-1")
    created = client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers).json()
    conflict = client.patch(f"{API}/products/{created['id']}", json={"sku": "autre-1"}, headers=admin_headers)
    assert conflict.status_code == 409 and error_code(conflict) == "sku_taken"
    missing = client.patch(f"{API}/products/{uuid.uuid4()}", json={"price_cents": 1}, headers=admin_headers)
    assert missing.status_code == 404


def test_delete_deactivates_product(client, db: Session, admin_headers, references):
    brand, category = references
    created = client.post(f"{API}/products", json=_payload(brand, category), headers=admin_headers).json()
    assert client.delete(f"{API}/products/{created['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/v1/products/{created['id']}").status_code == 404  # caché du public
    admin_view = client.get(f"{API}/products/{created['id']}", headers=admin_headers).json()
    assert admin_view["is_active"] is False  # toujours consultable par l'administrateur
    assert db.get(Product, uuid.UUID(created["id"])) is not None  # jamais supprimé
    listing = client.get(f"{API}/products", params={"is_active": "false"}, headers=admin_headers).json()
    assert [p["id"] for p in listing["items"]] == [created["id"]]
    reactivated = client.patch(
        f"{API}/products/{created['id']}", json={"is_active": True}, headers=admin_headers
    )
    assert reactivated.json()["is_active"] is True


def test_admin_product_list_is_paginated(client, admin_headers, make_product):
    for i in range(3):
        make_product(f"LIST-{i}")
    body = client.get(f"{API}/products", params={"size": 2}, headers=admin_headers).json()
    assert (body["total"], len(body["items"]), body["size"]) == (3, 2, 2)
    assert client.get(f"{API}/products", params={"size": 51}, headers=admin_headers).status_code == 422


# ---------------------------------------------------------------------------
# Images (URL https seulement)
# ---------------------------------------------------------------------------
def test_add_and_remove_images(client, admin_headers, make_product):
    product = make_product("IMG-1")
    url = f"{API}/products/{product.id}/images"
    first = client.post(
        url, json={"url": "https://cdn.example.com/a.jpg", "alt_fr": "Vue avant"}, headers=admin_headers
    )
    second = client.post(url, json={"url": "https://cdn.example.com/b.jpg"}, headers=admin_headers)
    assert (first.status_code, second.status_code) == (201, 201)
    assert (first.json()["position"], second.json()["position"]) == (0, 1)
    duplicate = client.post(
        url, json={"url": "https://cdn.example.com/c.jpg", "position": 1}, headers=admin_headers
    )
    assert duplicate.status_code == 409 and error_code(duplicate) == "image_position_taken"
    detail = client.get(f"/api/v1/products/{product.id}").json()
    assert detail["main_image_url"] == "https://cdn.example.com/a.jpg" and len(detail["images"]) == 2
    image_id = first.json()["id"]
    assert client.delete(f"{url}/{image_id}", headers=admin_headers).status_code == 204
    assert client.delete(f"{url}/{image_id}", headers=admin_headers).status_code == 404


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://cdn.example.com/a.jpg",
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
        "https://user:secret@cdn.example.com/a.jpg",
        "https://localhost/a.jpg",
        "https://cdn.example.com/a b.jpg",
        "//cdn.example.com/a.jpg",
        "https://" + "a" * 500 + ".com",
    ],
)
def test_unsafe_image_urls_are_refused(client, admin_headers, make_product, bad_url):
    product = make_product("IMG-2")
    response = client.post(
        f"{API}/products/{product.id}/images", json={"url": bad_url}, headers=admin_headers
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------
def test_category_crud(client, admin_headers):
    root = client.post(
        f"{API}/categories",
        json={"name_fr": "Outils", "name_en": "Tools", "slug": "outils"},
        headers=admin_headers,
    )
    assert root.status_code == 201
    child = client.post(
        f"{API}/categories",
        json={
            "name_fr": "Perceuses",
            "name_en": "Drills",
            "slug": "perceuses",
            "parent_id": root.json()["id"],
        },
        headers=admin_headers,
    ).json()
    renamed = client.patch(
        f"{API}/categories/{child['id']}", json={"name_en": "Power drills"}, headers=admin_headers
    )
    assert renamed.json()["name_en"] == "Power drills" and renamed.json()["parent_id"] == root.json()["id"]
    moved = client.patch(f"{API}/categories/{child['id']}", json={"parent_id": None}, headers=admin_headers)
    assert moved.json()["parent_id"] is None
    tree = client.get("/api/v1/categories").json()
    assert {c["slug"] for c in tree} == {"outils", "perceuses"}
    assert client.delete(f"{API}/categories/{child['id']}", headers=admin_headers).status_code == 204


def test_category_errors(client, admin_headers, make_category, make_product):
    a = make_category("a")
    b = make_category("b", parent=a)
    cycle = client.patch(f"{API}/categories/{a.id}", json={"parent_id": str(b.id)}, headers=admin_headers)
    assert cycle.status_code == 422 and error_code(cycle) == "category_cycle"
    itself = client.patch(f"{API}/categories/{a.id}", json={"parent_id": str(a.id)}, headers=admin_headers)
    assert itself.status_code == 422
    duplicate = client.post(
        f"{API}/categories", json={"name_fr": "x", "name_en": "x", "slug": "a"}, headers=admin_headers
    )
    assert duplicate.status_code == 409 and error_code(duplicate) == "slug_taken"
    bad_slug = client.post(
        f"{API}/categories", json={"name_fr": "x", "name_en": "x", "slug": "Pas Bon"}, headers=admin_headers
    )
    assert bad_slug.status_code == 422
    orphan = client.post(
        f"{API}/categories",
        json={"name_fr": "x", "name_en": "x", "slug": "x", "parent_id": str(uuid.uuid4())},
        headers=admin_headers,
    )
    assert orphan.status_code == 404
    has_children = client.delete(f"{API}/categories/{a.id}", headers=admin_headers)
    assert has_children.status_code == 409 and error_code(has_children) == "category_has_children"
    make_product("CAT-1", category_id=b.id)
    in_use = client.delete(f"{API}/categories/{b.id}", headers=admin_headers)
    assert in_use.status_code == 409 and error_code(in_use) == "category_in_use"
    null_name = client.patch(f"{API}/categories/{a.id}", json={"name_fr": None}, headers=admin_headers)
    assert null_name.status_code == 422


# ---------------------------------------------------------------------------
# Marques
# ---------------------------------------------------------------------------
def test_brand_crud_and_logical_deactivation(client, admin_headers, make_category):
    created = client.post(f"{API}/brands", json={"name": "Castor", "slug": "castor"}, headers=admin_headers)
    assert created.status_code == 201 and created.json()["is_active"] is True
    brand_id = created.json()["id"]
    renamed = client.patch(f"{API}/brands/{brand_id}", json={"name": "Castor Outils"}, headers=admin_headers)
    assert renamed.json()["name"] == "Castor Outils"
    assert client.delete(f"{API}/brands/{brand_id}", headers=admin_headers).status_code == 204
    listed = client.get(f"{API}/brands", headers=admin_headers).json()
    assert [(b["id"], b["is_active"]) for b in listed] == [(brand_id, False)]  # conservée, désactivée
    category = make_category("outils")
    product = {
        "sku": "B-1",
        "name_fr": "x",
        "name_en": "x",
        "price_cents": 1,
        "brand_id": brand_id,
        "category_id": str(category.id),
    }
    refused = client.post(f"{API}/products", json=product, headers=admin_headers)
    assert refused.status_code == 422 and error_code(refused) == "brand_inactive"


def test_brand_uniqueness_ignores_case(client, admin_headers):
    client.post(f"{API}/brands", json={"name": "Boréal", "slug": "boreal"}, headers=admin_headers)
    same_name = client.post(
        f"{API}/brands", json={"name": "BORÉAL", "slug": "boreal-2"}, headers=admin_headers
    )
    assert same_name.status_code == 409 and error_code(same_name) == "brand_name_taken"
    same_slug = client.post(f"{API}/brands", json={"name": "Autre", "slug": "boreal"}, headers=admin_headers)
    assert same_slug.status_code == 409 and error_code(same_slug) == "slug_taken"
    assert (
        client.post(f"{API}/brands", json={"name": "", "slug": "vide"}, headers=admin_headers).status_code
        == 422
    )
    assert (
        client.patch(f"{API}/brands/{uuid.uuid4()}", json={"name": "x"}, headers=admin_headers).status_code
        == 404
    )


def test_category_deleted_while_becoming_used_is_409(db: Session, make_category, make_product, monkeypatch):
    """Accès concurrent : les vérifications préalables ne voient rien, mais un produit existe déjà."""
    from app.core.errors import Conflict
    from app.services import catalog_admin_service

    category = make_category("course")
    make_product("RACE-1", category_id=category.id)
    monkeypatch.setattr(db, "scalar", lambda *args, **kwargs: 0)  # « aucun enfant, aucun produit »
    with pytest.raises(Conflict) as excinfo:
        catalog_admin_service.delete_category(db, category.id)
    assert excinfo.value.code == "category_in_use"
    assert db.get(Category, category.id) is not None  # rien n'a été supprimé
