"""Accès aux données du panier (tables `carts` et `cart_items`). Aucune règle métier ici.

Les fonctions font `flush()` au besoin mais ne valident jamais la transaction : c'est le service
qui décide du `commit` (ou de tout annuler).
"""

import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models import Cart, CartItem, Inventory, Product, ProductImage


def get_by_user(db: Session, user_id: uuid.UUID) -> Cart | None:
    """Panier du client (un seul par client : `carts.user_id` est unique)."""
    return db.scalars(select(Cart).where(Cart.user_id == user_id)).first()


def create(db: Session, user_id: uuid.UUID) -> Cart:
    cart = Cart(user_id=user_id)
    db.add(cart)
    db.flush()  # obtient l'id sans valider la transaction
    return cart


def _main_image_url():
    """URL de la première image du produit (position la plus basse), en sous-requête corrélée."""
    return (
        select(ProductImage.url)
        .where(ProductImage.product_id == Product.id)
        .order_by(ProductImage.position)
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )


def list_lines(db: Session, cart_id: uuid.UUID) -> list[Row]:
    """Lignes du panier avec leur produit et son image principale, dans l'ordre d'ajout.

    Une seule requête pour tout le panier (pas de requête par article).
    """
    stmt = (
        select(CartItem, Product, _main_image_url().label("main_image_url"))
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.cart_id == cart_id)
        .order_by(CartItem.created_at, CartItem.id)
    )
    return list(db.execute(stmt).all())


def get_item(db: Session, cart_id: uuid.UUID, item_id: uuid.UUID) -> CartItem | None:
    """Ligne `item_id` SEULEMENT si elle appartient à ce panier (protection contre l'IDOR, A-D4)."""
    return db.scalars(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id)).first()


def get_item_by_product(db: Session, cart_id: uuid.UUID, product_id: uuid.UUID) -> CartItem | None:
    return db.scalars(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
    ).first()


def add_item(db: Session, item: CartItem) -> CartItem:
    db.add(item)
    db.flush()
    return item


def delete_item(db: Session, item: CartItem) -> None:
    db.delete(item)
    db.flush()


def available_by_product(
    db: Session, store_id: uuid.UUID, product_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Quantité disponible (`on_hand − reserved`, RA-A-02) par produit dans un magasin.

    Un produit sans ligne d'inventaire dans ce magasin est absent du dictionnaire (= 0 disponible).
    Cette valeur reste interne : elle n'est jamais renvoyée au client (A-CAT-02).
    """
    if not product_ids:
        return {}
    rows = db.execute(
        select(Inventory.product_id, Inventory.on_hand - Inventory.reserved).where(
            Inventory.store_id == store_id, Inventory.product_id.in_(product_ids)
        )
    ).all()
    return {product_id: available for product_id, available in rows}
