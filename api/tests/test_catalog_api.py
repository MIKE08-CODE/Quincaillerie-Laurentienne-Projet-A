"""API publique du catalogue (A-CAT-01, A-CAT-02, A-CAT-03), sur les données d'amorçage du L1."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, Category, Inventory, Product, Store
from tests.conftest import error_code

API = "/api/v1"


def _product(db: Session, sku: str) -> Product:
    return db.scalar(select(Product).where(Product.sku == sku))


# ---------------------------------------------------------------------------
# Catégories et magasins
# ---------------------------------------------------------------------------
def test_categories_tree(client, seeded):
    response = client.get(f"{API}/categories")
    assert response.status_code == 200
    roots = response.json()
    assert {r["slug"] for r in roots} >= {"outils", "plomberie", "electricite", "saisonnier"}
    outils = next(r for r in roots if r["slug"] == "outils")
    electriques = next(c for c in outils["children"] if c["slug"] == "outils-electriques")
    assert {c["slug"] for c in electriques["children"]} == {"perceuses", "scies-electriques", "ponceuses"}
    assert outils["name_en"] == "Tools"


def test_stores_list(client, seeded):
    response = client.get(f"{API}/stores")
    assert response.status_code == 200
    stores = response.json()
    assert len(stores) == 3
    assert all(s["opening_hours"]["mon"] for s in stores)
    assert {"Saint-Jérôme", "Sainte-Agathe-des-Monts", "Mont-Tremblant"} <= {
        s["name"].split("— ")[1] for s in stores
    }


# ---------------------------------------------------------------------------
# Liste paginée, tris et filtres (A-CAT-01)
# ---------------------------------------------------------------------------
def test_products_default_page(client, seeded):
    body = client.get(f"{API}/products").json()
    assert (body["page"], body["size"]) == (1, 20)
    assert body["total"] >= 150 and len(body["items"]) == 20
    item = body["items"][0]
    assert set(item) == {
        "id",
        "sku",
        "name_fr",
        "name_en",
        "brand",
        "price_cents",
        "main_image_url",
        "category_id",
    }
    assert item["main_image_url"].startswith("https://")


def test_page_size_is_capped_at_50(client, seeded):
    assert len(client.get(f"{API}/products", params={"size": 50}).json()["items"]) == 50
    for params in (
        {"size": 51},
        {"size": 0},
        {"page": 0},
        {"sort": "random"},
        {"category_id": "pas-un-uuid"},
    ):
        assert client.get(f"{API}/products", params=params).status_code == 422, params


def test_pagination_covers_all_products_without_duplicates(client, seeded):
    total = client.get(f"{API}/products").json()["total"]
    seen = []
    for page in range(1, total // 50 + 2):
        seen += [
            p["id"] for p in client.get(f"{API}/products", params={"size": 50, "page": page}).json()["items"]
        ]
    assert len(seen) == len(set(seen)) == total


@pytest.mark.parametrize(
    ("sort", "key", "reverse"),
    [
        ("price_asc", "price_cents", False),
        ("price_desc", "price_cents", True),
        ("name_asc", "name_fr", False),
    ],
)
def test_products_sorting(client, seeded, sort, key, reverse):
    items = client.get(f"{API}/products", params={"sort": sort, "size": 50}).json()["items"]
    values = [i[key] for i in items]
    if key == "price_cents":
        assert values == sorted(values, reverse=reverse)
    else:
        assert values[0] <= values[-1]


def test_name_sort_in_english(client, seeded):
    items = client.get(f"{API}/products", params={"sort": "name_desc", "lang": "en", "size": 50}).json()[
        "items"
    ]
    assert items[0]["name_en"] >= items[-1]["name_en"]


def test_newest_first(client, db: Session, seeded, make_product):
    newest = make_product("NEW-1")
    assert client.get(f"{API}/products").json()["items"][0]["id"] == str(newest.id)


def test_category_filter_includes_subcategories(client, db: Session, seeded):
    outils = db.scalar(select(Category).where(Category.slug == "outils-electriques"))
    body = client.get(f"{API}/products", params={"category_id": str(outils.id), "size": 50}).json()
    skus = {i["sku"] for i in body["items"]}
    assert {"PERC-18V", "SCIRC-714", "PONC-ORB5"} <= skus  # trois sous-catégories
    assert not any(s.startswith(("MART", "PEIN")) for s in skus)


def test_unknown_category_is_404(client, seeded):
    response = client.get(f"{API}/products", params={"category_id": str(uuid.uuid4())})
    assert response.status_code == 404 and error_code(response) == "category_not_found"


def test_brand_filter(client, db: Session, seeded):
    brand = db.scalar(select(Brand).where(Brand.slug == "hydra"))
    body = client.get(f"{API}/products", params={"brand_id": str(brand.id), "size": 50}).json()
    assert body["total"] == db.query(Product).filter(Product.brand_id == brand.id).count() > 0
    assert {i["brand"] for i in body["items"]} == {"Hydra"}


def test_inactive_products_are_hidden(client, db: Session, seeded):
    product = _product(db, "MART-16")
    product.is_active = False
    db.commit()
    total = client.get(f"{API}/products").json()["total"]
    assert total == db.query(Product).filter(Product.is_active.is_(True)).count()
    assert client.get(f"{API}/products/{product.id}").status_code == 404
    assert client.get(f"{API}/products/{product.id}/availability").status_code == 404
    assert "MART-16" not in _search_skus(client, "marteau")


# ---------------------------------------------------------------------------
# Fiche produit et disponibilité (A-CAT-02)
# ---------------------------------------------------------------------------
def test_product_detail_is_bilingual_and_complete(client, db: Session, seeded):
    product = _product(db, "PERC-18V")
    response = client.get(f"{API}/products/{product.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "PERC-18V" and body["brand"] == "Laurentide Pro"
    assert body["name_fr"].startswith("Perceuse") and body["name_en"].startswith("Cordless drill")
    assert body["description_fr"] and body["description_en"]
    assert body["specs"]["tension_v"] == 18
    assert body["images"][0]["url"].startswith("https://") and body["images"][0]["alt_en"]
    assert len(body["availability"]) == 3


def test_product_detail_errors(client, seeded):
    assert error_code(client.get(f"{API}/products/{uuid.uuid4()}")) == "product_not_found"
    assert client.get(f"{API}/products/123").status_code == 422


def test_availability_is_computed_from_real_stock(client, db: Session, seeded):
    product = _product(db, "PERC-18V")
    stores = db.scalars(select(Store).order_by(Store.name)).all()
    levels = [(0, 0), (3, 0), (40, 0)]  # rupture, stock faible (seuil 5), en stock
    for store, (on_hand, reserved) in zip(stores, levels, strict=True):
        inventory = db.get(Inventory, (product.id, store.id))
        inventory.on_hand, inventory.reserved = on_hand, reserved
    db.commit()
    availability = client.get(f"{API}/products/{product.id}/availability").json()
    by_store = {a["store_id"]: a["status"] for a in availability}
    assert [by_store[str(s.id)] for s in stores] == ["out_of_stock", "low_stock", "in_stock"]
    # Les quantités ne sont jamais exposées au public.
    assert all(set(a) == {"store_id", "store_name", "status"} for a in availability)
    detail = client.get(f"{API}/products/{product.id}").json()
    assert "on_hand" not in str(detail) and "reserved" not in str(detail)


def test_store_without_inventory_row_is_out_of_stock(client, db: Session, seeded, make_store):
    make_store("Nouveau magasin")
    product = _product(db, "PERC-18V")
    availability = client.get(f"{API}/products/{product.id}/availability").json()
    assert {a["store_name"]: a["status"] for a in availability}["Nouveau magasin"] == "out_of_stock"


# ---------------------------------------------------------------------------
# Recherche plein texte (A-CAT-03)
# ---------------------------------------------------------------------------
def _search_skus(client, q: str, **params) -> list[str]:
    response = client.get(f"{API}/search", params={"q": q, "size": 50, **params})
    assert response.status_code == 200, response.text
    return [i["sku"] for i in response.json()["items"]]


@pytest.mark.parametrize("q", ["perceuse", "drill", "Perceuses", "DRILLS"])
def test_search_finds_drills_in_french_and_english(client, seeded, q):
    skus = _search_skus(client, q)
    assert {"PERC-18V", "PERC-20V", "PERCP-SDS"} <= set(skus)
    # « drill » trouve aussi les forets (« drill bit ») et les ancrages « self-drilling » (racinisation).
    assert all(s.startswith(("PERC", "FORET", "ANCR")) for s in skus)


def test_french_search_only_returns_drill_related_products(client, seeded):
    assert all(s.startswith(("PERC", "FORET")) for s in _search_skus(client, "perceuse"))


@pytest.mark.parametrize("q", ["equerre", "équerre", "ÉQUERRE", "square"])
def test_search_is_accent_insensitive(client, seeded, q):
    assert {"EQUE-MEN", "EQUE-COMB"} <= set(_search_skus(client, q))


def test_search_ranks_name_matches_first(client, seeded):
    skus = _search_skus(client, "marteau")
    assert skus and all(s.startswith("MART") for s in skus[:5])


def test_search_pagination_and_validation(client, seeded):
    body = client.get(f"{API}/search", params={"q": "perceuse", "size": 2}).json()
    assert len(body["items"]) == 2 and body["total"] >= 9
    assert client.get(f"{API}/search").status_code == 422
    assert client.get(f"{API}/search", params={"q": ""}).status_code == 422
    blank = client.get(f"{API}/search", params={"q": "   "})
    assert blank.status_code == 422 and error_code(blank) == "query_blank"
    assert client.get(f"{API}/search", params={"q": "x" * 101}).status_code == 422


@pytest.mark.parametrize("q", ["the and of", "zzzzqqq", "'; DROP TABLE products; --", "a & b | !c"])
def test_search_handles_stopwords_unknown_and_special_input(client, db: Session, seeded, q):
    assert _search_skus(client, q) == []
    assert db.query(Product).count() >= 150  # aucune injection possible : paramètres liés


def test_public_catalog_is_rate_limited(client):
    """120 requêtes par minute et par adresse IP sur les routes publiques (ENF-05, contrat §5)."""
    statuses = [client.get(f"{API}/stores").status_code for _ in range(120)]
    assert statuses == [200] * 120
    blocked = client.get(f"{API}/stores")
    assert blocked.status_code == 429 and error_code(blocked) == "rate_limited"
    assert blocked.headers["Retry-After"]


def test_public_responses_never_contain_stock_quantities(client, db: Session, seeded):
    product = _product(db, "MESU-25")
    for path in (
        f"/products/{product.id}",
        f"/products/{product.id}/availability",
        "/products",
        "/search?q=ruban",
    ):
        body = client.get(f"{API}{path}").text
        for field in ("on_hand", "reserved", "reorder_threshold", "quantity", "version"):
            assert f'"{field}"' not in body, (path, field)
