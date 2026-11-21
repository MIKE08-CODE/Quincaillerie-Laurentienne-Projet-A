"""Catalogue : catégories, marques, produits et images (cahier A.6 ; A-CAT-01 à 03, A-ADM-01).

Choix de conception (voir docs/architecture/catalogue-l1.md) :
- `brands` est une entité à part entière (A-ADM-01 exige un CRUD des marques; A.6 autorise
  l'ajout d'entités). Le nom n'est pas recopié dans `products` : on le lit par jointure.
- Unicité insensible à la casse des marques : index unique sur `lower(name)`, comme pour
  `users.email` (aucune extension citext).
- `products.search_vector` est une colonne GÉNÉRÉE par PostgreSQL à partir des noms et descriptions
  FR/EN, avec les configurations `fr_unaccent` et `en_unaccent` (créées par la migration) qui
  retirent les accents avant la racinisation : « equerre » trouve « équerre » (A-CAT-03).
- Les produits ne sont jamais supprimés : ils sont désactivés (`is_active`), car les stocks,
  mouvements et commandes y font référence.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Format des identifiants lisibles dans les URL : minuscules, chiffres et tirets.
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

# Expression de la colonne générée. Elle doit rester IDENTIQUE dans la migration (Alembic ne compare
# pas les expressions générées) : un test vérifie la définition réellement présente en base.
SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('public.fr_unaccent'::regconfig, coalesce(name_fr, '')), 'A') || "
    "setweight(to_tsvector('public.en_unaccent'::regconfig, coalesce(name_en, '')), 'A') || "
    "setweight(to_tsvector('public.fr_unaccent'::regconfig, coalesce(description_fr, '')), 'C') || "
    "setweight(to_tsvector('public.en_unaccent'::regconfig, coalesce(description_en, '')), 'C')"
)


class Category(Base):
    """Arborescence auto-référencée (p. ex. Outils > Outils électriques > Perceuses).

    Les cycles sont refusés deux fois : par le service (message clair) et par un déclencheur SQL
    (`categories_prevent_cycle`), qui protège aussi les écritures faites hors de l'API.
    """

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        CheckConstraint(f"slug ~ '{SLUG_PATTERN}'", name="slug_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name_fr: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Brand(Base):
    """Marque (A-ADM-01). Désactivation logique : une marque utilisée n'est jamais supprimée."""

    __tablename__ = "brands"
    __table_args__ = (
        Index("uq_brands_name_lower", text("lower(name)"), unique=True),
        CheckConstraint(f"slug ~ '{SLUG_PATTERN}'", name="slug_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="price_non_negative"),
        CheckConstraint("char_length(btrim(sku)) > 0", name="sku_not_blank"),
        CheckConstraint("jsonb_typeof(specs) = 'object'", name="specs_is_object"),
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_products_active_created", "is_active", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name_fr: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    description_fr: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    price_cents: Mapped[int] = mapped_column(BigInteger)  # jamais de nombre à virgule (RA-A-04)
    specs: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), deferred=True
    )

    brand: Mapped[Brand | None] = relationship(lazy="joined")
    images: Mapped[list["ProductImage"]] = relationship(
        order_by="ProductImage.position", cascade="all, delete-orphan", back_populates="product"
    )


class ProductImage(Base):
    """Image d'un produit, désignée par une URL https (aucun fournisseur de stockage au L1)."""

    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "position"),
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("url LIKE 'https://%'", name="url_https"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    alt_fr: Mapped[str | None] = mapped_column(String(250))
    alt_en: Mapped[str | None] = mapped_column(String(250))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="images")
