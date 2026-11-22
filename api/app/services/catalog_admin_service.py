"""Administration du catalogue (A-ADM-01) : produits, images, catégories et marques.

Règles :
- Les produits et les marques ne sont jamais supprimés : ils sont DÉSACTIVÉS (désactivation logique).
- Une catégorie ne peut être supprimée que si elle n'a ni sous-catégorie ni produit (sinon 409).
- Les doublons (SKU, slug, nom de marque sans tenir compte de la casse, position d'image) sont
  détectés par les contraintes SQL et traduits en 409; un cycle de catégories en 422.
- Les vérifications d'autorisation sont faites par le routeur (rôle administrateur, MFA).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import Brand, Category, Product, ProductImage
from app.schemas.catalog import (
    BrandCreate,
    BrandUpdate,
    CategoryCreate,
    CategoryUpdate,
    ImageCreate,
    ProductCreate,
    ProductUpdate,
)
from app.services import catalog_service
from app.services.image_storage import ImageStorage
from app.services.image_validation import validate_image

_UNIQUE_ERRORS = {
    "uq_products_sku": ("sku_taken", "Ce SKU est déjà utilisé."),
    "uq_categories_slug": ("slug_taken", "Ce slug de catégorie est déjà utilisé."),
    "uq_brands_slug": ("slug_taken", "Ce slug de marque est déjà utilisé."),
    "uq_brands_name_lower": ("brand_name_taken", "Une marque porte déjà ce nom."),
    "uq_product_images_product_id": ("image_position_taken", "Une image occupe déjà cette position."),
}


def _commit(db: Session) -> None:
    """Valide la transaction en traduisant les violations de contraintes en erreurs de l'API."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        diag = getattr(exc.orig, "diag", None)
        constraint = getattr(diag, "constraint_name", None)
        if constraint in _UNIQUE_ERRORS:
            raise Conflict(*_UNIQUE_ERRORS[constraint]) from None
        if constraint in ("ck_categories_no_cycle", "ck_categories_not_own_parent"):
            raise ValidationFailed(
                "category_cycle", "Une catégorie ne peut pas descendre d'elle-même."
            ) from None
        raise


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------
def _check_brand(db: Session, brand_id: uuid.UUID | None) -> None:
    if brand_id is None:
        return
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise NotFound("brand_not_found", "Marque introuvable.")
    if not brand.is_active:
        raise ValidationFailed("brand_inactive", "Cette marque est désactivée.")


def _check_category(db: Session, category_id: uuid.UUID | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise NotFound("category_not_found", "Catégorie introuvable.")


def admin_view(db: Session, product: Product) -> dict:
    return {
        **catalog_service.product_detail(db, product),
        "brand_id": product.brand_id,
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def list_products(db: Session, *, page: int, size: int, is_active: bool | None) -> tuple[list[Product], int]:
    query = select(Product)
    if is_active is not None:
        query = query.where(Product.is_active.is_(is_active))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = db.scalars(query.order_by(Product.sku).offset((page - 1) * size).limit(size)).all()
    return list(products), total


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    return catalog_service.get_product(db, product_id, include_inactive=True)


def create_product(db: Session, data: ProductCreate) -> Product:
    _check_brand(db, data.brand_id)
    _check_category(db, data.category_id)
    product = Product(**data.model_dump())
    db.add(product)
    _commit(db)
    db.refresh(product)
    return product


def update_product(db: Session, product_id: uuid.UUID, data: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("brand_id") is not None and changes["brand_id"] != product.brand_id:
        _check_brand(db, changes["brand_id"])
    if changes.get("category_id") is not None:
        _check_category(db, changes["category_id"])
    for field, value in changes.items():
        setattr(product, field, value)
    _commit(db)
    db.refresh(product)
    return product


def deactivate_product(db: Session, product_id: uuid.UUID) -> None:
    product = get_product(db, product_id)
    product.is_active = False
    _commit(db)


def add_image(db: Session, product_id: uuid.UUID, data: ImageCreate) -> ProductImage:
    product = get_product(db, product_id)
    position = data.position
    if position is None:
        last = db.scalar(select(func.max(ProductImage.position)).where(ProductImage.product_id == product.id))
        position = 0 if last is None else last + 1
    image = ProductImage(
        product_id=product.id, url=data.url, alt_fr=data.alt_fr, alt_en=data.alt_en, position=position
    )
    db.add(image)
    _commit(db)
    db.refresh(image)
    return image


def upload_image(
    db: Session,
    product_id: uuid.UUID,
    data: bytes,
    *,
    declared_type: str | None,
    alt_fr: str | None,
    alt_en: str | None,
    storage: ImageStorage,
) -> ProductImage:
    """Valide le fichier, le confie au stockage persistant, puis l'ajoute au produit.

    Le nom du fichier est généré par le serveur (jamais celui du client). Si l'enregistrement en base
    échoue, le fichier déjà stocké est supprimé pour ne pas laisser d'orphelin.
    """
    get_product(db, product_id)  # 404 avant tout traitement du fichier
    settings = get_settings()
    info = validate_image(
        data,
        declared_type=declared_type,
        max_bytes=settings.image_max_bytes,
        max_dimension=settings.image_max_dimension,
    )
    key = f"products/{product_id}/{uuid.uuid4().hex}.{info.extension}"
    url = storage.save(key, data, info.content_type)
    try:
        return add_image(db, product_id, ImageCreate(url=url, alt_fr=alt_fr, alt_en=alt_en))
    except Exception:
        storage.delete(url)
        raise


def delete_image(
    db: Session, product_id: uuid.UUID, image_id: uuid.UUID, storage: ImageStorage | None = None
) -> None:
    image = db.get(ProductImage, image_id)
    if image is None or image.product_id != product_id:
        raise NotFound("image_not_found", "Image introuvable.")
    url = image.url
    db.delete(image)
    _commit(db)
    if storage is not None:
        storage.delete(url)  # sans effet pour une image désignée par une URL externe


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------
def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name_fr, Category.id)))


def _get_category(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFound("category_not_found", "Catégorie introuvable.")
    return category


def create_category(db: Session, data: CategoryCreate) -> Category:
    if data.parent_id is not None:
        _get_category(db, data.parent_id)
    category = Category(**data.model_dump())
    db.add(category)
    _commit(db)
    db.refresh(category)
    return category


def update_category(db: Session, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
    category = _get_category(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("parent_id") is not None:
        _get_category(db, changes["parent_id"])
    for field, value in changes.items():
        setattr(category, field, value)
    _commit(db)  # le déclencheur SQL refuse tout cycle (traduit en 422 `category_cycle`)
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: uuid.UUID) -> None:
    category = _get_category(db, category_id)
    if db.scalar(select(func.count()).where(Category.parent_id == category.id)):
        raise Conflict("category_has_children", "Cette catégorie contient des sous-catégories.")
    if db.scalar(select(func.count()).where(Product.category_id == category.id)):
        raise Conflict("category_in_use", "Des produits appartiennent à cette catégorie.")
    db.delete(category)
    try:
        _commit(db)
    except IntegrityError:
        # Catégorie devenue utilisée entre la vérification et la suppression (accès concurrent).
        raise Conflict("category_in_use", "Cette catégorie est utilisée.") from None


# ---------------------------------------------------------------------------
# Marques
# ---------------------------------------------------------------------------
def list_brands(db: Session) -> list[Brand]:
    return list(db.scalars(select(Brand).order_by(func.lower(Brand.name))))


def _get_brand(db: Session, brand_id: uuid.UUID) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise NotFound("brand_not_found", "Marque introuvable.")
    return brand


def create_brand(db: Session, data: BrandCreate) -> Brand:
    brand = Brand(**data.model_dump())
    db.add(brand)
    _commit(db)
    db.refresh(brand)
    return brand


def update_brand(db: Session, brand_id: uuid.UUID, data: BrandUpdate) -> Brand:
    brand = _get_brand(db, brand_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    _commit(db)
    db.refresh(brand)
    return brand


def deactivate_brand(db: Session, brand_id: uuid.UUID) -> None:
    brand = _get_brand(db, brand_id)
    brand.is_active = False
    _commit(db)
