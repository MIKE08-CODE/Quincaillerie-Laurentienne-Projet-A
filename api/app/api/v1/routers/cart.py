"""Routes /api/v1/cart/* (A-ORD-01, A-ORD-02) : panier côté serveur, partagé par le web et le mobile.

Aucune logique métier ici (ENF-11) : on lit la requête, on appelle cart_service, on renvoie la réponse.
Toutes les routes sont réservées aux CLIENTS : 401 sans jeton, 403 pour le personnel (qui n'achète pas
avec son compte de travail). Chaque route renvoie le panier complet à jour.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.auth import ErrorResponse
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartOut, CartStoreUpdate
from app.services import cart_service

router = APIRouter(
    prefix="/cart",
    tags=["panier"],
    responses={
        401: {"model": ErrorResponse, "description": "Jeton absent, expiré ou invalide."},
        403: {"model": ErrorResponse, "description": "Réservé aux clients (`insufficient_role`)."},
        422: {
            "model": ErrorResponse,
            "description": "Données invalides (champ inconnu, quantité hors 1 à 20…).",
        },
    },
)

# Une seule dépendance pour toutes les routes : le rôle est relu en base à chaque requête (deps.py).
client_only = require_roles(UserRole.CLIENT)

ERR_404_ITEM = {
    404: {"model": ErrorResponse, "description": "Article absent de votre panier (`cart_item_not_found`)."}
}


@router.get("", response_model=CartOut, summary="Consulter son panier")
def get_cart(user: User = Depends(client_only), db: Session = Depends(get_db)) -> dict:
    """Panier du client connecté, identique sur le web et le mobile (A-ORD-01).

    Les prix sont les prix **actuels** (en cents). Chaque article indique s'il est disponible dans le
    magasin choisi (`is_available`, `unavailable_reason`) ; les quantités en stock ne sont jamais données.
    Sans panier encore créé, la réponse est un panier vide.
    """
    return cart_service.get_cart(db, user)


@router.put(
    "",
    response_model=CartOut,
    summary="Choisir le magasin de cueillette",
    responses={404: {"model": ErrorResponse, "description": "Magasin inconnu (`store_not_found`)."}},
)
def set_store(
    body: CartStoreUpdate, user: User = Depends(client_only), db: Session = Depends(get_db)
) -> dict:
    """Choisit le magasin de cueillette (A-ORD-02) ; la disponibilité des articles est recalculée."""
    return cart_service.set_store(db, user, body.store_id)


@router.post(
    "/items",
    response_model=CartOut,
    summary="Ajouter un produit",
    responses={404: {"model": ErrorResponse, "description": "Produit inconnu (`product_not_found`)."}},
)
def add_item(body: CartItemCreate, user: User = Depends(client_only), db: Session = Depends(get_db)) -> dict:
    """Ajoute un produit actif. S'il est déjà dans le panier, les quantités **s'additionnent**.

    - Au plus 20 unités par produit (RA-A-07) : au-delà, 422 `quantity_limit`.
    - Produit désactivé : 422 `product_inactive`.
    - **Aucun prix n'est accepté** : un champ `price_cents` est refusé (422), le prix vient de la base.
    """
    return cart_service.add_item(db, user, body.product_id, body.quantity)


@router.patch(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Changer la quantité d'un article",
    responses=ERR_404_ITEM,
)
def update_item(
    item_id: uuid.UUID, body: CartItemUpdate, user: User = Depends(client_only), db: Session = Depends(get_db)
) -> dict:
    """Fixe la quantité exacte (1 à 20) d'un article du panier."""
    return cart_service.update_item(db, user, item_id, body.quantity)


@router.delete(
    "/items/{item_id}", response_model=CartOut, summary="Retirer un article", responses=ERR_404_ITEM
)
def remove_item(item_id: uuid.UUID, user: User = Depends(client_only), db: Session = Depends(get_db)) -> dict:
    """Retire l'article et renvoie le panier à jour. L'article d'un autre client répond 404."""
    return cart_service.remove_item(db, user, item_id)
