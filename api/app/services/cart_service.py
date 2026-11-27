"""Panier côté serveur (A-ORD-01, A-ORD-02, A-ORD-03, RA-A-07).

Les fonctions reçoivent une session de base de données et des valeurs simples; elles ne connaissent
ni FastAPI ni HTTP (ENF-11). Elles lèvent des AppError et valident la transaction elles-mêmes.

Règles :
- Un panier par client, conservé en base : le même panier est vu sur le web et le mobile (A-ORD-01).
- Le panier est créé au premier ajout; une simple lecture n'écrit rien (choix C3).
- Les prix viennent TOUJOURS de la base, au prix actuel; aucun prix n'est accepté du client (A-ORD-03).
  Ils seront figés au paiement (RA-A-09, `/checkout`).
- Ajouter un produit déjà présent ADDITIONNE les quantités, sans dépasser 20 (RA-A-07, choix C1).
- Chaque article indique s'il peut être commandé dans le magasin choisi (A-ORD-02, choix C4), sans
  jamais exposer la quantité en stock.
- Un produit désactivé après son ajout reste visible, signalé et exclu du sous-total (choix C5).
- Accès concurrents (web et mobile en même temps) : la ligne de l'utilisateur est verrouillée pendant
  chaque modification (choix C7), donc deux ajouts simultanés ne dépassent pas 20 ni ne créent de doublon.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFound, ValidationFailed
from app.models import Cart, CartItem, Product, Store, User
from app.models.order import MAX_ITEM_QUANTITY
from app.repositories import cart_repository, user_repository


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
def get_cart(db: Session, user: User) -> dict:
    """Panier du client, ou panier vide s'il n'existe pas encore (sans le créer)."""
    return _view(db, cart_repository.get_by_user(db, user.id))


def _view(db: Session, cart: Cart | None) -> dict:
    """Construit la réponse : prix actuels, sous-total et disponibilité dans le magasin choisi."""
    if cart is None:
        return {
            "store_id": None,
            "store_name": None,
            "items": [],
            "item_count": 0,
            "subtotal_cents": 0,
            "has_unavailable_items": False,
        }

    lines = cart_repository.list_lines(db, cart.id)
    store = db.get(Store, cart.store_id) if cart.store_id else None
    available = (
        cart_repository.available_by_product(db, store.id, [product.id for _, product, _ in lines])
        if store
        else {}
    )

    items = []
    subtotal = 0
    for item, product, main_image_url in lines:
        reason = _unavailable_reason(product, item.quantity, store, available)
        line_total = product.price_cents * item.quantity
        if product.is_active:
            subtotal += line_total  # un produit désactivé est exclu du sous-total (C5)
        items.append(
            {
                "id": item.id,
                "product_id": product.id,
                "sku": product.sku,
                "name_fr": product.name_fr,
                "name_en": product.name_en,
                "main_image_url": main_image_url,
                "unit_price_cents": product.price_cents,
                "quantity": item.quantity,
                "line_total_cents": line_total,
                "is_available": reason is None,
                "unavailable_reason": reason,
            }
        )

    return {
        "store_id": store.id if store else None,
        "store_name": store.name if store else None,
        "items": items,
        "item_count": sum(item["quantity"] for item in items),
        "subtotal_cents": subtotal,
        "has_unavailable_items": any(not item["is_available"] for item in items),
    }


def _unavailable_reason(
    product: Product, quantity: int, store: Store | None, available: dict[uuid.UUID, int]
) -> str | None:
    """Pourquoi l'article ne peut pas être commandé tel quel, ou None s'il le peut (A-ORD-02)."""
    if not product.is_active:
        return "product_inactive"
    if store is None:
        return "no_store_selected"
    if available.get(product.id, 0) < quantity:
        return "insufficient_stock"
    return None


# ---------------------------------------------------------------------------
# Modifications
# ---------------------------------------------------------------------------
def _locked_cart(db: Session, user: User) -> Cart:
    """Panier du client, créé au besoin, sous verrou.

    On verrouille la ligne de l'UTILISATEUR (et non celle du panier, qui peut ne pas exister encore) :
    toutes les modifications du panier d'un même client s'exécutent donc l'une après l'autre, même si
    le web et le mobile envoient une requête au même moment. Cela empêche aussi de créer deux paniers.
    """
    user_repository.lock_by_id(db, user.id)
    return cart_repository.get_by_user(db, user.id) or cart_repository.create(db, user.id)


def _commit_and_view(db: Session, cart: Cart) -> dict:
    db.commit()
    return _view(db, cart)


def set_store(db: Session, user: User, store_id: uuid.UUID) -> dict:
    """Choisit le magasin de cueillette (A-ORD-02). La disponibilité est recalculée pour ce magasin."""
    if db.get(Store, store_id) is None:
        raise NotFound("store_not_found", "Magasin introuvable.")
    cart = _locked_cart(db, user)
    cart.store_id = store_id
    return _commit_and_view(db, cart)


def add_item(db: Session, user: User, product_id: uuid.UUID, quantity: int) -> dict:
    """Ajoute un produit; s'il est déjà dans le panier, les quantités s'additionnent (C1)."""
    product = db.get(Product, product_id)
    if product is None:
        raise NotFound("product_not_found", "Produit introuvable.")
    if not product.is_active:
        raise ValidationFailed("product_inactive", "Ce produit n'est plus offert.")

    cart = _locked_cart(db, user)
    item = cart_repository.get_item_by_product(db, cart.id, product.id)
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > MAX_ITEM_QUANTITY:
        raise ValidationFailed(
            "quantity_limit", f"Au plus {MAX_ITEM_QUANTITY} unités de ce produit par commande."
        )

    if item is None:
        cart_repository.add_item(db, CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity))
    else:
        item.quantity = new_quantity
    return _commit_and_view(db, cart)


def update_item(db: Session, user: User, item_id: uuid.UUID, quantity: int) -> dict:
    """Fixe la quantité exacte d'un article (boutons + et − du mobile, C2)."""
    cart = _locked_cart(db, user)
    item = _own_item(db, cart, item_id)
    item.quantity = quantity  # 1 à 20, déjà vérifié par le schéma
    return _commit_and_view(db, cart)


def remove_item(db: Session, user: User, item_id: uuid.UUID) -> dict:
    """Retire un article du panier."""
    cart = _locked_cart(db, user)
    cart_repository.delete_item(db, _own_item(db, cart, item_id))
    return _commit_and_view(db, cart)


def _own_item(db: Session, cart: Cart, item_id: uuid.UUID) -> CartItem:
    """Article de CE panier. Celui d'un autre client répond 404, comme un article inexistant :
    on ne révèle pas qu'il existe (IDOR, défi A-D4)."""
    item = cart_repository.get_item(db, cart.id, item_id)
    if item is None:
        raise NotFound("cart_item_not_found", "Article introuvable dans votre panier.")
    return item
