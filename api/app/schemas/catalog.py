"""Schémas du catalogue : lecture publique (A-CAT-01 à 03) et administration (A-ADM-01).

- Les réponses publiques ne donnent JAMAIS les quantités en stock : seulement un statut calculé
  (`in_stock`, `low_stock`, `out_of_stock`), conformément à A-CAT-02 et au contrat (§8.3).
- Les entrées refusent les champs inconnus (`extra="forbid"`) et retirent les espaces superflus.
- Modification partielle (PATCH) : un champ absent n'est pas modifié; `null` efface un champ
  facultatif; `null` sur un champ obligatoire est refusé (422).
"""

import json
import re
import uuid
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models.catalog import SLUG_PATTERN

AvailabilityStatus = Literal["in_stock", "low_stock", "out_of_stock"]
ProductSort = Literal["newest", "price_asc", "price_desc", "name_asc", "name_desc"]

SKU_PATTERN = r"^[A-Z0-9][A-Z0-9._-]{0,63}$"
MAX_PRICE_CENTS = 100_000_000  # 1 000 000 $ : borne anti-erreur de saisie
MAX_SPECS_KEYS = 50
MAX_SPECS_JSON_LENGTH = 10_000

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
BrandName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Slug = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=SLUG_PATTERN)
]
AltText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=250)]
SpecValue = str | int | float | bool | list[str | int | float]


# ---------------------------------------------------------------------------
# Lecture publique
# ---------------------------------------------------------------------------
class CategoryNode(BaseModel):
    id: uuid.UUID
    slug: str
    name_fr: str
    name_en: str
    children: list["CategoryNode"] = Field(description="Sous-catégories, triées par nom français.")


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: str
    phone: str | None
    opening_hours: dict = Field(
        description='Heures d\'ouverture par jour (`mon` à `sun`), p. ex. `["08:00", "21:00"]`.'
    )


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    alt_fr: str | None
    alt_en: str | None
    position: int


class StoreAvailability(BaseModel):
    store_id: uuid.UUID
    store_name: str
    status: AvailabilityStatus = Field(
        description="`in_stock` (En stock), `low_stock` (Stock faible) ou `out_of_stock` (Rupture). "
        "Calculé à partir du stock réel; les quantités ne sont jamais exposées."
    )


class ProductSummary(BaseModel):
    id: uuid.UUID
    sku: str
    name_fr: str
    name_en: str
    brand: str | None = Field(description="Nom de la marque.")
    price_cents: int = Field(description="Prix en cents (entier).")
    main_image_url: str | None
    category_id: uuid.UUID | None


class ProductDetail(ProductSummary):
    description_fr: str | None
    description_en: str | None
    specs: dict = Field(description="Caractéristiques techniques (objet JSON).")
    images: list[ImageOut]
    availability: list[StoreAvailability]


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------
class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _normalize_sku(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


def _check_specs(value: dict | None) -> dict | None:
    if value is None:
        return value
    if len(value) > MAX_SPECS_KEYS:
        raise ValueError(f"au plus {MAX_SPECS_KEYS} caractéristiques")
    for key in value:
        if not 1 <= len(key) <= 60:
            raise ValueError("chaque nom de caractéristique doit faire de 1 à 60 caractères")
    if len(json.dumps(value, ensure_ascii=False)) > MAX_SPECS_JSON_LENGTH:
        raise ValueError("caractéristiques trop volumineuses")
    return value


class ProductCreate(_Input):
    sku: str = Field(
        pattern=SKU_PATTERN,
        description="Code unique (lettres majuscules, chiffres, `.`, `_`, `-`; converti en majuscules).",
        examples=["PERC-18V-001"],
    )
    name_fr: Name
    name_en: Name
    description_fr: Description | None = None
    description_en: Description | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    price_cents: int = Field(strict=True, ge=0, le=MAX_PRICE_CENTS, examples=[8999])
    specs: dict[str, SpecValue] = Field(default_factory=dict, examples=[{"tension_v": 18, "batteries": 2}])
    is_active: bool = True

    _sku = field_validator("sku", mode="before")(_normalize_sku)
    _specs = field_validator("specs")(_check_specs)


# Champs obligatoires du produit : ils peuvent être omis d'un PATCH, mais pas mis à `null`.
_PRODUCT_REQUIRED = ("sku", "name_fr", "name_en", "price_cents", "specs", "is_active")


class ProductUpdate(_Input):
    """Modification partielle (PATCH). Tous les champs sont facultatifs."""

    sku: str | None = Field(default=None, pattern=SKU_PATTERN)
    name_fr: Name | None = None
    name_en: Name | None = None
    description_fr: Description | None = None
    description_en: Description | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    price_cents: int | None = Field(default=None, strict=True, ge=0, le=MAX_PRICE_CENTS)
    specs: dict[str, SpecValue] | None = None
    is_active: bool | None = None

    _sku = field_validator("sku", mode="before")(_normalize_sku)
    _specs = field_validator("specs")(_check_specs)

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> "ProductUpdate":
        for name in _PRODUCT_REQUIRED:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"`{name}` ne peut pas être null")
        return self


class ProductAdminOut(ProductDetail):
    brand_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


def _check_image_url(value: str) -> str:
    """URL d'image sûre : https uniquement, hôte présent, sans identifiants ni caractères de contrôle."""
    if len(value) > 500 or re.search(r"[\s\x00-\x1f\x7f]", value):
        raise ValueError("URL invalide")
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or "." not in parts.hostname:
        raise ValueError("l'URL doit commencer par https:// et désigner un hôte valide")
    if parts.username is not None or parts.password is not None:
        raise ValueError("l'URL ne doit pas contenir d'identifiants")
    return value


class ImageCreate(_Input):
    url: str = Field(
        description="URL https de l'image.", examples=["https://images.example.com/perc-18v-001.jpg"]
    )
    alt_fr: AltText | None = None
    alt_en: AltText | None = None
    position: int | None = Field(default=None, ge=0, le=1000, description="Ordre; à la fin par défaut.")

    _url = field_validator("url")(_check_image_url)


class CategoryCreate(_Input):
    name_fr: CategoryName
    name_en: CategoryName
    slug: Slug = Field(examples=["perceuses"])
    parent_id: uuid.UUID | None = None


class CategoryUpdate(_Input):
    name_fr: CategoryName | None = None
    name_en: CategoryName | None = None
    slug: Slug | None = None
    parent_id: uuid.UUID | None = Field(default=None, description="`null` place la catégorie à la racine.")

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> "CategoryUpdate":
        for name in ("name_fr", "name_en", "slug"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"`{name}` ne peut pas être null")
        return self


class CategoryAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    slug: str
    name_fr: str
    name_en: str
    created_at: datetime
    updated_at: datetime


class BrandCreate(_Input):
    name: BrandName = Field(examples=["Laurentide Pro"])
    slug: Slug = Field(examples=["laurentide-pro"])


class BrandUpdate(_Input):
    name: BrandName | None = None
    slug: Slug | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> "BrandUpdate":
        for name in ("name", "slug", "is_active"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"`{name}` ne peut pas être null")
        return self


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
