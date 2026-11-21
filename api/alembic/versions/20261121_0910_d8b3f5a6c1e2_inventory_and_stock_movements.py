"""stocks : inventory et grand livre stock_movements (ajout seulement)

`stock_movements.order_id` est créée ici SANS clé étrangère : la table `orders` n'existe pas encore.
La clé étrangère est ajoutée par la migration suivante (e2c9a4b7d3f1).

Le déclencheur `stock_movements_append_only` refuse UPDATE et DELETE ligne par ligne. TRUNCATE
(opération d'administration, utilisée par la suite de tests pour vider la base) n'est pas visé.

Revision ID: d8b3f5a6c1e2
Revises: c4a1e7d2b9f0
Create Date: 2026-11-21 09:10:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8b3f5a6c1e2"
down_revision: str | None = "c4a1e7d2b9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MOVEMENT_TYPES = (
    "receipt",
    "sale",
    "reservation",
    "release",
    "adjustment",
    "return",
    "transfer_in",
    "transfer_out",
)

# Doit rester identique à app.models.inventory.MOVEMENT_SIGN_RULE.
MOVEMENT_SIGN_RULE = (
    "(type IN ('receipt', 'return', 'transfer_in', 'reservation') AND quantity > 0)"
    " OR (type IN ('sale', 'transfer_out', 'release') AND quantity < 0)"
    " OR (type = 'adjustment' AND quantity <> 0)"
)


def upgrade() -> None:
    op.create_table(
        "inventory",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("on_hand", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_threshold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("on_hand >= 0", name=op.f("ck_inventory_on_hand_non_negative")),
        sa.CheckConstraint("reserved >= 0", name=op.f("ck_inventory_reserved_non_negative")),
        sa.CheckConstraint("reserved <= on_hand", name=op.f("ck_inventory_reserved_le_on_hand")),
        sa.CheckConstraint("reorder_threshold >= 0", name=op.f("ck_inventory_reorder_threshold_non_negative")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_inventory_version_positive")),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_inventory_product_id_products"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name=op.f("fk_inventory_store_id_stores"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("product_id", "store_id", name=op.f("pk_inventory")),
    )
    op.create_index(op.f("ix_inventory_store_id"), "inventory", ["store_id"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(*MOVEMENT_TYPES, name="stock_movement_type", native_enum=False, create_constraint=True, length=20),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(MOVEMENT_SIGN_RULE, name=op.f("ck_stock_movements_quantity_sign_matches_type")),
        sa.CheckConstraint(
            "type <> 'adjustment' OR (reason IS NOT NULL AND char_length(btrim(reason)) > 0)",
            name=op.f("ck_stock_movements_adjustment_has_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "store_id"],
            ["inventory.product_id", "inventory.store_id"],
            name="fk_stock_movements_inventory",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_stock_movements_actor_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
    )
    op.create_index(op.f("ix_stock_movements_actor_id"), "stock_movements", ["actor_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_order_id"), "stock_movements", ["order_id"], unique=False)
    op.create_index(
        "ix_stock_movements_product_store_created",
        "stock_movements",
        ["product_id", "store_id", "created_at"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION public.stock_movements_append_only() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
        BEGIN
            RAISE EXCEPTION 'stock_movements is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_stock_movements_append_only BEFORE UPDATE OR DELETE ON public.stock_movements "
        "FOR EACH ROW EXECUTE FUNCTION public.stock_movements_append_only()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_stock_movements_append_only ON public.stock_movements")
    op.execute("DROP FUNCTION IF EXISTS public.stock_movements_append_only()")
    op.drop_index("ix_stock_movements_product_store_created", table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_order_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_actor_id"), table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index(op.f("ix_inventory_store_id"), table_name="inventory")
    op.drop_table("inventory")
