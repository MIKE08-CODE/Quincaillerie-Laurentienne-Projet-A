"""Schémas du panier (A-ORD-01, A-ORD-02, RA-A-07).

Choix de sécurité :
- Les entrées refusent les champs inconnus (`extra="forbid"`) : un `price_cents` envoyé par le client
  est rejeté (422). Le prix vient TOUJOURS de la base (A-ORD-03, défi A-D2).
- Les quantités sont des entiers stricts de 1 à 20 (RA-A-07) : « 2 » (texte) ou 2.5 sont refusés.
- La réponse ne donne jamais la quantité en stock : seulement `is_available` et une raison (A-CAT-02).
"""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import MAX_ITEM_QUANTITY

# Raisons pour lesquelles un article ne pourra pas être commandé tel quel (A-ORD-02).
UnavailableReason = Literal["no_store_selected", "insufficient_stock", "product_inactive"]

Quantity = Field(
    strict=True,
    ge=1,
    le=MAX_ITEM_QUANTITY,
    description=f"Quantité de 1 à {MAX_ITEM_QUANTITY} (RA-A-07).",
    examples=[2],
)


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Entrées
# ---------------------------------------------------------------------------
class CartStoreUpdate(_Input):
    """Corps de `PUT /cart` : choix du magasin de cueillette (A-ORD-02)."""

    store_id: uuid.UUID = Field(description="Magasin de cueillette (voir `GET /stores`).")


class CartItemCreate(_Input):
    """Corps de `POST /cart/items`. Aucun prix : il est lu en base."""

    product_id: uuid.UUID = Field(description="Produit à ajouter (doit être actif).")
    quantity: int = Quantity


class CartItemUpdate(_Input):
    """Corps de `PATCH /cart/items/{item_id}` : nouvelle quantité exacte de l'article."""

    quantity: int = Quantity


# ---------------------------------------------------------------------------
# Sorties
# ---------------------------------------------------------------------------
class CartItemOut(BaseModel):
    id: uuid.UUID = Field(description="Identifiant de la ligne du panier (pour `PATCH`/`DELETE`).")
    product_id: uuid.UUID
    sku: str
    name_fr: str
    name_en: str
    main_image_url: str | None
    unit_price_cents: int = Field(
        description="Prix ACTUEL du produit, en cents (figé seulement au paiement)."
    )
    quantity: int
    line_total_cents: int = Field(description="`unit_price_cents × quantity`.")
    is_available: bool = Field(
        description="`true` si l'article peut être commandé dans le magasin choisi, à cette quantité."
    )
    unavailable_reason: UnavailableReason | None = Field(
        description="`no_store_selected` (aucun magasin choisi), `insufficient_stock` (pas assez de stock "
        "dans ce magasin) ou `product_inactive` (produit retiré du catalogue); `null` si disponible."
    )


class CartOut(BaseModel):
    """Panier complet, renvoyé par toutes les routes `/cart` (le client n'a pas besoin d'un second appel)."""

    store_id: uuid.UUID | None = Field(description="Magasin de cueillette choisi, ou `null`.")
    store_name: str | None
    items: list[CartItemOut] = Field(description="Articles, dans l'ordre d'ajout.")
    item_count: int = Field(description="Nombre total d'unités dans le panier.")
    subtotal_cents: int = Field(
        description="Somme des lignes des produits actifs, en cents. Sans taxes : elles sont calculées "
        "par `/checkout` (A-ORD-03)."
    )
    has_unavailable_items: bool = Field(description="`true` si au moins un article n'est pas disponible.")
