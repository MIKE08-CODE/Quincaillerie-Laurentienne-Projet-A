"""Amorçage reproductible et idempotent des données du L1 : `python -m app.seed.seed_l1`.

- 3 magasins, l'arborescence des catégories, les marques et au moins 150 produits bilingues.
- Stocks par magasin, initialisés UNIQUEMENT par des mouvements `receipt` (grand livre, A-INV-01).
- Idempotent : chaque élément a un identifiant déterministe (UUID v5) ou une clé naturelle (slug,
  SKU). Un élément déjà présent n'est ni dupliqué ni modifié : une relance ne crée rien, et les
  modifications faites ensuite par un administrateur sont conservées.
- Les quantités de départ sont déterministes (dérivées du SKU et du magasin) : chaque exécution sur
  une base vide produit exactement les mêmes données.

Aucun secret ni donnée personnelle : marques, adresses et téléphones sont fictifs.
"""

import argparse
import hashlib
import sys
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Brand, Category, Inventory, Product, ProductImage, Store
from app.seed import data_l1
from app.services import inventory_service

# Espace de noms des UUID v5 de l'amorçage (valeur fixe : les identifiants restent stables).
SEED_NAMESPACE = uuid.UUID("6f1c3a52-2d4e-4b8a-9f61-0c7e5d3a9b14")
SEED_REASON = "seed_l1"
REORDER_THRESHOLD = 5
IMAGE_BASE_URL = "https://images.quincaillerie-laurentienne.example/products"


def seed_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}")


def initial_quantity(sku: str, store_key: str) -> int:
    """Quantité de départ déterministe : environ 15 % de ruptures, 15 % de stocks faibles."""
    value = int(hashlib.sha256(f"{sku}|{store_key}".encode()).hexdigest()[:8], 16)
    bucket = value % 100
    if bucket < 15:
        return 0
    if bucket < 30:
        return 1 + value % REORDER_THRESHOLD  # de 1 à 5 : stock faible
    return 10 + value % 51  # de 10 à 60


@dataclass
class SeedReport:
    created: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(
            ("stores", "categories", "brands", "products", "images", "inventory", "movements"), 0
        )
    )

    @property
    def total_created(self) -> int:
        return sum(self.created.values())


def _seed_stores(db: Session, report: SeedReport) -> dict[str, uuid.UUID]:
    ids = {}
    for store in data_l1.STORES:
        store_id = seed_uuid("store", store["key"])
        ids[store["key"]] = store_id
        if db.get(Store, store_id) is None:
            db.add(
                Store(
                    id=store_id,
                    name=store["name"],
                    address=store["address"],
                    phone=store["phone"],
                    opening_hours=store["opening_hours"],
                )
            )
            report.created["stores"] += 1
    db.flush()
    return ids


def _seed_categories(db: Session, report: SeedReport) -> dict[str, uuid.UUID]:
    ids = {c.slug: c.id for c in db.scalars(select(Category))}
    for slug, parent_slug, name_fr, name_en in data_l1.CATEGORIES:
        if slug in ids:
            continue
        category = Category(
            id=seed_uuid("category", slug),
            slug=slug,
            parent_id=ids[parent_slug] if parent_slug else None,
            name_fr=name_fr,
            name_en=name_en,
        )
        db.add(category)
        db.flush()  # le parent doit exister avant ses enfants (déclencheur anti-cycle)
        ids[slug] = category.id
        report.created["categories"] += 1
    return ids


def _seed_brands(db: Session, report: SeedReport) -> dict[str, uuid.UUID]:
    ids = {b.slug: b.id for b in db.scalars(select(Brand))}
    for slug, name in data_l1.BRANDS:
        if slug not in ids:
            brand = Brand(id=seed_uuid("brand", slug), slug=slug, name=name)
            db.add(brand)
            ids[slug] = brand.id
            report.created["brands"] += 1
    db.flush()
    return ids


def _products() -> list[dict]:
    """Déplie les familles en produits (une variante = un produit = un SKU)."""
    products = []
    for family in data_l1.FAMILIES:
        for code, label_fr, label_en, price_cents, specs in family["variants"]:
            sku = f"{family['sku']}-{code}"
            products.append(
                {
                    "sku": sku,
                    "name_fr": family["name_fr"].format(v=label_fr),
                    "name_en": family["name_en"].format(v=label_en),
                    "description_fr": family["desc_fr"],
                    "description_en": family["desc_en"],
                    "category": family["category"],
                    "brand": family["brand"],
                    "price_cents": price_cents,
                    "specs": {**family["specs"], **specs},
                }
            )
    return products


def run(db: Session) -> SeedReport:
    """Exécute l'amorçage dans UNE transaction (tout ou rien) et la valide."""
    report = SeedReport()
    store_ids = _seed_stores(db, report)
    category_ids = _seed_categories(db, report)
    brand_ids = _seed_brands(db, report)
    product_ids = dict(db.execute(select(Product.sku, Product.id)).tuples().all())
    stocked = set(db.execute(select(Inventory.product_id, Inventory.store_id)).tuples().all())

    for data in _products():
        product_id = product_ids.get(data["sku"])
        if product_id is None:
            product_id = seed_uuid("product", data["sku"])
            db.add(
                Product(
                    id=product_id,
                    sku=data["sku"],
                    name_fr=data["name_fr"],
                    name_en=data["name_en"],
                    description_fr=data["description_fr"],
                    description_en=data["description_en"],
                    category_id=category_ids[data["category"]],
                    brand_id=brand_ids[data["brand"]],
                    price_cents=data["price_cents"],
                    specs=data["specs"],
                )
            )
            db.add(
                ProductImage(
                    id=seed_uuid("image", data["sku"]),
                    product_id=product_id,
                    url=f"{IMAGE_BASE_URL}/{data['sku'].lower()}.jpg",
                    alt_fr=data["name_fr"],
                    alt_en=data["name_en"],
                    position=0,
                )
            )
            report.created["products"] += 1
            report.created["images"] += 1

        for store_key, store_id in store_ids.items():
            if (product_id, store_id) in stocked:
                continue  # stock déjà initialisé : aucun nouveau mouvement
            quantity = initial_quantity(data["sku"], store_key)
            inventory_service.create_initial_stock(
                db,
                product_id=product_id,
                store_id=store_id,
                quantity=quantity,
                reorder_threshold=REORDER_THRESHOLD,
                reason=SEED_REASON,
            )
            report.created["inventory"] += 1
            report.created["movements"] += quantity > 0

    db.commit()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Amorçage des données de démonstration du L1.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Autoriser l'exécution quand APP_ENV=production (démonstration L1 seulement).",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    target = make_url(settings.database_url.get_secret_value())
    print(f"Base visée : {target.host}:{target.port}/{target.database} (APP_ENV={settings.app_env})")
    if settings.app_env == "production" and not args.allow_production:
        print(
            "Refusé : APP_ENV=production. Relancer avec --allow-production si c'est voulu.", file=sys.stderr
        )
        return 2

    from app.db.session import SessionLocal  # import tardif : la connexion n'est ouverte qu'ici

    with SessionLocal() as db:
        report = run(db)
    for name, count in report.created.items():
        print(f"  {name:<11} créés : {count}")
    print("Aucune nouvelle donnée : base déjà amorcée." if report.total_created == 0 else "Amorçage terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
