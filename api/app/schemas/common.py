"""Schémas partagés par plusieurs modules de l'API."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 50  # A-CAT-01 : listes paginées, 50 éléments au maximum par page
DEFAULT_PAGE_SIZE = 20


class Page(BaseModel, Generic[T]):
    """Page d'une collection (contrat d'API §4.2)."""

    items: list[T] = Field(description="Éléments de la page.")
    page: int = Field(ge=1, description="Numéro de la page courante (à partir de 1).")
    size: int = Field(ge=1, le=MAX_PAGE_SIZE, description="Nombre d'éléments demandés par page.")
    total: int = Field(ge=0, description="Nombre total d'éléments correspondant à la requête.")
