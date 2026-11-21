"""catalogue : categories, brands, products, product_images et recherche plein texte FR/EN

Crée l'extension `unaccent`, les configurations de recherche `fr_unaccent` et `en_unaccent`
(accents retirés avant la racinisation), la colonne générée `products.search_vector` avec son
index GIN, et le déclencheur qui refuse les cycles dans l'arborescence des catégories.

Revision ID: c4a1e7d2b9f0
Revises: aa6b82a168aa
Create Date: 2026-11-21 09:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4a1e7d2b9f0"
down_revision: str | None = "aa6b82a168aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SLUG_CHECK = "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'"

# Doit rester identique à app.models.catalog.SEARCH_VECTOR_SQL (vérifié par un test).
SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('public.fr_unaccent'::regconfig, coalesce(name_fr, '')), 'A') || "
    "setweight(to_tsvector('public.en_unaccent'::regconfig, coalesce(name_en, '')), 'A') || "
    "setweight(to_tsvector('public.fr_unaccent'::regconfig, coalesce(description_fr, '')), 'C') || "
    "setweight(to_tsvector('public.en_unaccent'::regconfig, coalesce(description_en, '')), 'C')"
)


def upgrade() -> None:
    # --- Recherche plein texte insensible aux accents (A-CAT-03) -------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public")
    for config, base, stem in (("fr_unaccent", "french", "french_stem"), ("en_unaccent", "english", "english_stem")):
        op.execute(f"CREATE TEXT SEARCH CONFIGURATION public.{config} (COPY = pg_catalog.{base})")
        op.execute(
            f"ALTER TEXT SEARCH CONFIGURATION public.{config} "
            f"ALTER MAPPING FOR hword, hword_part, word WITH public.unaccent, pg_catalog.{stem}"
        )

    # --- categories ----------------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name_fr", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name=op.f("ck_categories_not_own_parent")),
        sa.CheckConstraint(SLUG_CHECK, name=op.f("ck_categories_slug_format")),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], name=op.f("fk_categories_parent_id_categories"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)

    # Déclencheur anti-cycle : remonte les ancêtres du nouveau parent; si la catégorie elle-même
    # y figure, l'arborescence formerait une boucle.
    op.execute(
        """
        CREATE FUNCTION public.categories_prevent_cycle() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
        BEGIN
            IF NEW.parent_id IS NOT NULL AND EXISTS (
                WITH RECURSIVE ancestors(id, parent_id) AS (
                    SELECT c.id, c.parent_id FROM public.categories c WHERE c.id = NEW.parent_id
                    UNION
                    SELECT c.id, c.parent_id FROM public.categories c
                    JOIN ancestors a ON c.id = a.parent_id
                )
                SELECT 1 FROM ancestors WHERE id = NEW.id
            ) THEN
                RAISE EXCEPTION 'categories: cycle detected for %', NEW.id
                    USING ERRCODE = 'check_violation', CONSTRAINT = 'ck_categories_no_cycle';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_categories_prevent_cycle BEFORE INSERT OR UPDATE OF parent_id "
        "ON public.categories FOR EACH ROW EXECUTE FUNCTION public.categories_prevent_cycle()"
    )

    # --- brands --------------------------------------------------------------------------------
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(SLUG_CHECK, name=op.f("ck_brands_slug_format")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brands")),
        sa.UniqueConstraint("slug", name=op.f("uq_brands_slug")),
    )
    op.create_index("uq_brands_name_lower", "brands", [sa.text("lower(name)")], unique=True)

    # --- products ------------------------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name_fr", sa.String(length=200), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("description_fr", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "specs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_SQL, persisted=True),
            nullable=True,
        ),
        sa.CheckConstraint("price_cents >= 0", name=op.f("ck_products_price_non_negative")),
        sa.CheckConstraint("char_length(btrim(sku)) > 0", name=op.f("ck_products_sku_not_blank")),
        sa.CheckConstraint("jsonb_typeof(specs) = 'object'", name=op.f("ck_products_specs_is_object")),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"], name=op.f("fk_products_brand_id_brands"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_products_category_id_categories"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("sku", name=op.f("uq_products_sku")),
    )
    op.create_index(op.f("ix_products_brand_id"), "products", ["brand_id"], unique=False)
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index("ix_products_active_created", "products", ["is_active", "created_at"], unique=False)
    op.create_index(
        "ix_products_search_vector", "products", ["search_vector"], unique=False, postgresql_using="gin"
    )

    # --- product_images ------------------------------------------------------------------------
    op.create_table(
        "product_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt_fr", sa.String(length=250), nullable=True),
        sa.Column("alt_en", sa.String(length=250), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_product_images_position_non_negative")),
        sa.CheckConstraint("url LIKE 'https://%'", name=op.f("ck_product_images_url_https")),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_product_images_product_id_products"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_images")),
        sa.UniqueConstraint("product_id", "position", name=op.f("uq_product_images_product_id")),
    )
    op.create_index(op.f("ix_product_images_product_id"), "product_images", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_images_product_id"), table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("ix_products_search_vector", table_name="products", postgresql_using="gin")
    op.drop_index("ix_products_active_created", table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_index(op.f("ix_products_brand_id"), table_name="products")
    op.drop_table("products")
    op.drop_index("uq_brands_name_lower", table_name="brands")
    op.drop_table("brands")
    op.execute("DROP TRIGGER IF EXISTS trg_categories_prevent_cycle ON public.categories")
    op.execute("DROP FUNCTION IF EXISTS public.categories_prevent_cycle()")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_table("categories")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS public.en_unaccent")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS public.fr_unaccent")
    # L'extension n'est retirée que si plus rien n'en dépend (comportement par défaut, sans CASCADE).
    op.execute("DROP EXTENSION IF EXISTS unaccent")
