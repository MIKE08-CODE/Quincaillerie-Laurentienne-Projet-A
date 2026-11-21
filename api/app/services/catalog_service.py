"""Lecture publique du catalogue (A-CAT-01, A-CAT-02, A-CAT-03).

Seuls les produits ACTIFS sont visibles du public; un produit désactivé répond 404.
Toutes les requêtes sont paramétrées (aucune concaténation de texte reçu dans le SQL).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFound
from app.models import Brand, Category, Inventory, Product, ProductImage, Store
from app.services.inventory_service import OUT_OF_STOCK, availability_status

FR_CONFIG = literal_column("'public.fr_unaccent'::regconfig")
EN_CONFIG = literal_column("'public.en_unaccent'::regconfig")


@dataclass(frozen=True)
class ProductPage:
    items: list[dict]
    total: int


# ---------------------------------------------------------------------------
# Catégories et magasins
# ---------------------------------------------------------------------------
def category_tree(db: Session) -> list[dict]:
    """Arborescence complète (liste non paginée, bornée : contrat §4.2), triée par nom français."""
    categories = db.scalars(select(Category).order_by(Category.name_fr, Category.id)).all()
    nodes = {
        c.id: {"id": c.id, "slug": c.slug, "name_fr": c.name_fr, "name_en": c.name_en, "children": []}
        for c in categories
    }
    roots: list[dict] = []
    for c in categories:
        (nodes[c.parent_id]["children"] if c.parent_id in nodes else roots).append(nodes[c.id])
    return roots


def category_with_descendants(db: Session, category_id: uuid.UUID) -> list[uuid.UUID]:
    """La catégorie et toutes ses sous-catégories (CTE récursive). 404 si elle n'existe pas."""
    if db.get(Category, category_id) is None:
        raise NotFound("category_not_found", "Catégorie introuvable.")
    tree = select(Category.id).where(Category.id == category_id).cte("tree", recursive=True)
    tree = tree.union_all(select(Category.id).where(Category.parent_id == tree.c.id))
    return list(db.scalars(select(tree.c.id)))


def list_stores(db: Session) -> list[Store]:
    return list(db.scalars(select(Store).order_by(Store.name, Store.id)))


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------
def _main_image_url():
    return (
        select(ProductImage.url)
        .where(ProductImage.product_id == Product.id)
        .order_by(ProductImage.position)
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )


def _summary_query() -> Select:
    return select(
        Product, Brand.name.label("brand_name"), _main_image_url().label("main_image_url")
    ).outerjoin(Brand, Brand.id == Product.brand_id)


def _summary(product: Product, brand_name: str | None, main_image_url: str | None) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name_fr": product.name_fr,
        "name_en": product.name_en,
        "brand": brand_name,
        "price_cents": product.price_cents,
        "main_image_url": main_image_url,
        "category_id": product.category_id,
    }


_SORTS = {
    "newest": lambda lang: (Product.created_at.desc(), Product.sku),
    "price_asc": lambda lang: (Product.price_cents.asc(), Product.sku),
    "price_desc": lambda lang: (Product.price_cents.desc(), Product.sku),
    "name_asc": lambda lang: ((Product.name_en if lang == "en" else Product.name_fr).asc(), Product.sku),
    "name_desc": lambda lang: ((Product.name_en if lang == "en" else Product.name_fr).desc(), Product.sku),
}


def _paginate(db: Session, query: Select, *, page: int, size: int, order_by: tuple) -> ProductPage:
    total = db.scalar(select(func.count()).select_from(query.with_only_columns(Product.id).subquery()))
    rows = db.execute(query.order_by(*order_by).offset((page - 1) * size).limit(size)).all()
    return ProductPage(items=[_summary(*row) for row in rows], total=total or 0)


def list_products(
    db: Session,
    *,
    page: int,
    size: int,
    sort: str,
    lang: str = "fr",
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
) -> ProductPage:
    """Liste paginée des produits actifs, avec filtre par catégorie (sous-catégories incluses)."""
    query = _summary_query().where(Product.is_active.is_(True))
    if category_id is not None:
        query = query.where(Product.category_id.in_(category_with_descendants(db, category_id)))
    if brand_id is not None:
        query = query.where(Product.brand_id == brand_id)
    return _paginate(db, query, page=page, size=size, order_by=_SORTS[sort](lang))


def search_products(db: Session, *, q: str, page: int, size: int) -> ProductPage:
    """Recherche plein texte FR + EN, insensible aux accents (A-CAT-03), triée par pertinence."""
    ts_query = func.websearch_to_tsquery(FR_CONFIG, q).op("||")(func.websearch_to_tsquery(EN_CONFIG, q))
    rank = func.ts_rank_cd(Product.search_vector, ts_query)
    query = _summary_query().where(Product.is_active.is_(True), Product.search_vector.op("@@")(ts_query))
    return _paginate(db, query, page=page, size=size, order_by=(rank.desc(), Product.name_fr, Product.sku))


def get_product(db: Session, product_id: uuid.UUID, *, include_inactive: bool = False) -> Product:
    query = select(Product).options(selectinload(Product.images)).where(Product.id == product_id)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    product = db.scalar(query)
    if product is None:
        raise NotFound("product_not_found", "Produit introuvable.")
    return product


def availability(db: Session, product_id: uuid.UUID) -> list[dict]:
    """Statut par magasin pour TOUS les magasins (sans ligne d'inventaire : rupture)."""
    rows = db.execute(
        select(Store.id, Store.name, Inventory.on_hand, Inventory.reserved, Inventory.reorder_threshold)
        .outerjoin(Inventory, (Inventory.store_id == Store.id) & (Inventory.product_id == product_id))
        .order_by(Store.name, Store.id)
    ).all()
    return [
        {
            "store_id": store_id,
            "store_name": name,
            "status": OUT_OF_STOCK if on_hand is None else availability_status(on_hand, reserved, threshold),
        }
        for store_id, name, on_hand, reserved, threshold in rows
    ]


def product_detail(db: Session, product: Product) -> dict:
    images = list(product.images)
    return {
        **_summary(product, product.brand.name if product.brand else None, images[0].url if images else None),
        "description_fr": product.description_fr,
        "description_en": product.description_en,
        "specs": product.specs,
        "images": images,
        "availability": availability(db, product.id),
    }
