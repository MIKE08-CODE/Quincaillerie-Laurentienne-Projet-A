"""Amorçage L1 : volumes, idempotence, invariants des stocks et bilinguisme."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    StockMovement,
    StockMovementType,
    Store,
)
from app.seed import seed_l1
from app.services import inventory_service


def _counts(db: Session) -> dict[str, int]:
    models = {
        "stores": Store,
        "categories": Category,
        "brands": Brand,
        "products": Product,
        "images": ProductImage,
        "inventory": Inventory,
        "movements": StockMovement,
    }
    return {name: db.scalar(select(func.count()).select_from(model)) for name, model in models.items()}


def test_seed_creates_the_l1_volumes(db: Session, seeded):
    counts = _counts(db)
    assert counts["stores"] == 3
    assert counts["products"] >= 150
    assert counts["inventory"] == counts["products"] * 3  # une ligne par produit et par magasin
    assert counts["categories"] >= 20 and counts["brands"] >= 5
    assert seeded.created == counts  # le rapport décrit exactement ce qui a été créé


def test_seed_is_idempotent(db: Session, seeded):
    before = _counts(db)
    second = seed_l1.run(db)
    assert second.total_created == 0
    assert _counts(db) == before


def test_seed_keeps_admin_changes_on_rerun(db: Session, seeded):
    product = db.scalar(select(Product).where(Product.sku == "PERC-18V"))
    product.price_cents = 1
    db.commit()
    seed_l1.run(db)
    db.refresh(product)
    assert product.price_cents == 1


def test_stock_comes_only_from_receipt_movements(db: Session, seeded):
    types = set(db.scalars(select(StockMovement.type).distinct()))
    assert types == {StockMovementType.RECEIPT}
    assert inventory_service.find_discrepancies(db) == []
    statuses = {
        inventory_service.availability_status(i.on_hand, i.reserved, i.reorder_threshold)
        for i in db.scalars(select(Inventory))
    }
    assert statuses == {"in_stock", "low_stock", "out_of_stock"}  # démonstration des trois statuts


def test_products_are_bilingual_and_complete(db: Session, seeded):
    for product in db.scalars(select(Product)):
        assert product.name_fr.strip() and product.name_en.strip()
        assert product.description_fr and product.description_en
        assert product.price_cents > 0 and product.specs
        assert product.category_id and product.brand_id
    names = db.execute(select(func.count(func.distinct(Product.name_fr)), func.count())).one()
    assert names[0] == names[1]  # noms distincts


def test_category_tree_has_three_levels(db: Session, seeded):
    perceuses = db.scalar(select(Category).where(Category.slug == "perceuses"))
    parent = db.get(Category, perceuses.parent_id)
    grandparent = db.get(Category, parent.parent_id)
    assert (grandparent.slug, parent.slug) == ("outils", "outils-electriques")


def test_seed_quantities_are_deterministic():
    assert seed_l1.initial_quantity("PERC-18V", "saint-jerome") == seed_l1.initial_quantity(
        "PERC-18V", "saint-jerome"
    )
    assert seed_l1.seed_uuid("product", "PERC-18V") == seed_l1.seed_uuid("product", "PERC-18V")


def test_seed_refuses_production_without_flag(monkeypatch, capsys):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert seed_l1.main([]) == 2
    assert "Refusé" in capsys.readouterr().err
