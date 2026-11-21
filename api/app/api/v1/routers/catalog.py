"""Routes publiques du catalogue : /categories, /stores, /products, /search (A-CAT-01 à 03).

Aucune authentification : visiteurs, clients et applications mobile et bureau consultent le même
catalogue. Seuls les produits actifs sont visibles; la disponibilité ne donne qu'un statut.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.rate_limit import PUBLIC_READ_LIMIT, limiter
from app.db.session import get_db
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import (
    CategoryNode,
    ProductDetail,
    ProductSort,
    ProductSummary,
    StoreAvailability,
    StoreOut,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.services import catalog_service

router = APIRouter(tags=["catalogue"])

ERR_404 = {
    404: {"model": ErrorResponse, "description": "Produit ou catégorie introuvable (`product_not_found`, …)."}
}
ERR_422 = {
    422: {"model": ErrorResponse, "description": "Paramètre invalide (p. ex. `size` > 50, `page` < 1)."}
}

PageParam = Query(1, ge=1, description="Numéro de page (à partir de 1).")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Éléments par page (50 au maximum).")


@router.get("/categories", response_model=list[CategoryNode], summary="Arborescence des catégories")
@limiter.limit(PUBLIC_READ_LIMIT)
def list_categories(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    """Toutes les catégories, en arbre (`children`), noms FR et EN. Liste complète non paginée."""
    return catalog_service.category_tree(db)


@router.get("/stores", response_model=list[StoreOut], summary="Magasins")
@limiter.limit(PUBLIC_READ_LIMIT)
def list_stores(request: Request, db: Session = Depends(get_db)) -> list:
    """Les magasins (adresse, téléphone, heures d'ouverture). Liste complète non paginée."""
    return catalog_service.list_stores(db)


@router.get(
    "/products",
    response_model=Page[ProductSummary],
    summary="Liste paginée des produits",
    responses={**ERR_404, **ERR_422},
)
@limiter.limit(PUBLIC_READ_LIMIT)
def list_products(
    request: Request,
    page: int = PageParam,
    size: int = SizeParam,
    sort: ProductSort = Query("newest", description="Tri : nouveauté, prix ou nom."),
    lang: Literal["fr", "en"] = Query("fr", description="Langue utilisée pour le tri par nom."),
    category_id: uuid.UUID | None = Query(None, description="Catégorie (ses sous-catégories sont incluses)."),
    brand_id: uuid.UUID | None = Query(None, description="Marque."),
    db: Session = Depends(get_db),
) -> dict:
    """Produits actifs. Le filtre `category_id` inclut toutes les sous-catégories (A-CAT-01)."""
    result = catalog_service.list_products(
        db, page=page, size=size, sort=sort, lang=lang, category_id=category_id, brand_id=brand_id
    )
    return {"items": result.items, "page": page, "size": size, "total": result.total}


@router.get(
    "/products/{product_id}",
    response_model=ProductDetail,
    summary="Fiche produit",
    responses={**ERR_404, **ERR_422},
)
@limiter.limit(PUBLIC_READ_LIMIT)
def get_product(request: Request, product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Nom et description FR/EN, SKU, prix, images, caractéristiques et disponibilité par magasin."""
    return catalog_service.product_detail(db, catalog_service.get_product(db, product_id))


@router.get(
    "/products/{product_id}/availability",
    response_model=list[StoreAvailability],
    summary="Disponibilité par magasin",
    responses={**ERR_404, **ERR_422},
)
@limiter.limit(PUBLIC_READ_LIMIT)
def get_availability(request: Request, product_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    """Statut calculé à partir du stock réel : `in_stock`, `low_stock` ou `out_of_stock` (A-CAT-02)."""
    catalog_service.get_product(db, product_id)  # 404 si inconnu ou désactivé
    return catalog_service.availability(db, product_id)


@router.get(
    "/search",
    response_model=Page[ProductSummary],
    summary="Recherche plein texte FR/EN",
    responses=ERR_422,
)
@limiter.limit(PUBLIC_READ_LIMIT)
def search(
    request: Request,
    q: str = Query(min_length=1, max_length=100, description="Texte recherché, en français ou en anglais."),
    page: int = PageParam,
    size: int = SizeParam,
    db: Session = Depends(get_db),
) -> dict:
    """Recherche dans les noms et descriptions FR et EN, insensible aux accents (A-CAT-03).

    « perceuse » et « drill » trouvent les perceuses; « equerre » trouve « équerre ».
    """
    text = q.strip()
    if not text:
        raise ValidationFailed("query_blank", "Le texte recherché est vide.")
    result = catalog_service.search_products(db, q=text, page=page, size=size)
    return {"items": result.items, "page": page, "size": size, "total": result.total}
