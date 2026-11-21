"""Routes /admin/* du catalogue (A-ADM-01), réservées aux ADMINISTRATEURS ayant complété la MFA.

Le contrôle est posé au niveau du routeur : aucune route de ce fichier n'est accessible sans le rôle
`admin` (401 sans jeton, 403 pour tout autre rôle ou sans MFA). Modification partielle par PATCH.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import UserRole
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import (
    BrandCreate,
    BrandOut,
    BrandUpdate,
    CategoryAdminOut,
    CategoryCreate,
    CategoryUpdate,
    ImageCreate,
    ImageOut,
    ProductAdminOut,
    ProductCreate,
    ProductUpdate,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.services import catalog_admin_service as service

router = APIRouter(
    prefix="/admin",
    tags=["administration du catalogue"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
    responses={
        401: {"model": ErrorResponse, "description": "Jeton absent, expiré ou invalide."},
        403: {"model": ErrorResponse, "description": "Rôle administrateur requis, ou MFA non complétée."},
        422: {"model": ErrorResponse, "description": "Données invalides."},
    },
)

ERR_404 = {404: {"model": ErrorResponse, "description": "Ressource introuvable."}}
ERR_409 = {409: {"model": ErrorResponse, "description": "Doublon ou ressource utilisée (`sku_taken`, …)."}}


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------
@router.get("/products", response_model=Page[ProductAdminOut], summary="Produits (actifs et désactivés)")
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    is_active: bool | None = Query(None, description="Filtrer par statut."),
    db: Session = Depends(get_db),
) -> dict:
    products, total = service.list_products(db, page=page, size=size, is_active=is_active)
    return {
        "items": [service.admin_view(db, p) for p in products],
        "page": page,
        "size": size,
        "total": total,
    }


@router.post(
    "/products",
    response_model=ProductAdminOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un produit",
    responses={**ERR_404, **ERR_409},
)
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> dict:
    return service.admin_view(db, service.create_product(db, data))


@router.get(
    "/products/{product_id}",
    response_model=ProductAdminOut,
    summary="Consulter un produit",
    responses=ERR_404,
)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return service.admin_view(db, service.get_product(db, product_id))


@router.patch(
    "/products/{product_id}",
    response_model=ProductAdminOut,
    summary="Modifier un produit (partiel)",
    responses={**ERR_404, **ERR_409},
)
def update_product(product_id: uuid.UUID, data: ProductUpdate, db: Session = Depends(get_db)) -> dict:
    """Seuls les champs envoyés sont modifiés; `null` efface un champ facultatif."""
    return service.admin_view(db, service.update_product(db, product_id, data))


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Désactiver un produit",
    responses=ERR_404,
)
def deactivate_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Désactivation logique (`is_active = false`) : le produit disparaît du catalogue public."""
    service.deactivate_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/products/{product_id}/images",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une image (URL https)",
    responses={**ERR_404, **ERR_409},
)
def add_image(product_id: uuid.UUID, data: ImageCreate, db: Session = Depends(get_db)):
    """Au L1, une image est désignée par une URL https; aucun fichier n'est téléversé."""
    return service.add_image(db, product_id, data)


@router.delete(
    "/products/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer une image",
    responses=ERR_404,
)
def delete_image(product_id: uuid.UUID, image_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    service.delete_image(db, product_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------
@router.get("/categories", response_model=list[CategoryAdminOut], summary="Catégories (liste à plat)")
def list_categories(db: Session = Depends(get_db)) -> list:
    return service.list_categories(db)


@router.post(
    "/categories",
    response_model=CategoryAdminOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une catégorie",
    responses={**ERR_404, **ERR_409},
)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return service.create_category(db, data)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryAdminOut,
    summary="Modifier une catégorie (partiel)",
    responses={**ERR_404, **ERR_409},
)
def update_category(category_id: uuid.UUID, data: CategoryUpdate, db: Session = Depends(get_db)):
    """Un déplacement qui créerait un cycle est refusé (422 `category_cycle`)."""
    return service.update_category(db, category_id, data)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une catégorie vide",
    responses={**ERR_404, **ERR_409},
)
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Refusé (409) si la catégorie contient des sous-catégories ou des produits."""
    service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Marques
# ---------------------------------------------------------------------------
@router.get("/brands", response_model=list[BrandOut], summary="Marques (actives et désactivées)")
def list_brands(db: Session = Depends(get_db)) -> list:
    return service.list_brands(db)


@router.post(
    "/brands",
    response_model=BrandOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une marque",
    responses=ERR_409,
)
def create_brand(data: BrandCreate, db: Session = Depends(get_db)):
    return service.create_brand(db, data)


@router.patch(
    "/brands/{brand_id}",
    response_model=BrandOut,
    summary="Modifier une marque (partiel)",
    responses={**ERR_404, **ERR_409},
)
def update_brand(brand_id: uuid.UUID, data: BrandUpdate, db: Session = Depends(get_db)):
    return service.update_brand(db, brand_id, data)


@router.delete(
    "/brands/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Désactiver une marque",
    responses=ERR_404,
)
def deactivate_brand(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Désactivation logique : la marque ne peut plus être attribuée à un produit."""
    service.deactivate_brand(db, brand_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
