"""Stockage persistant des images de produits (A-ADM-01), indépendant du fournisseur.

L'API ne garde AUCUN fichier : ni sur le disque de Render (éphémère, effacé à chaque déploiement), ni
dans PostgreSQL (la base gratuite de Neon est limitée et les images n'y ont pas leur place). Un
fournisseur de stockage d'objets reçoit le fichier et renvoie une URL https publique, enregistrée
dans `product_images.url` comme les images désignées par URL.

Implémentations :
- `DisabledStorage` (défaut hors test) : téléversement refusé avec 503 `image_storage_not_configured`;
- `MemoryStorage` (tests) : garde les octets en mémoire.

Le fournisseur de production (recommandation : Cloudinary, offre gratuite sans carte bancaire) sera
ajouté comme une nouvelle classe respectant `ImageStorage`, après l'accord du responsable du projet.
"""

from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import ServiceUnavailable


class ImageStorage(Protocol):
    def save(self, key: str, data: bytes, content_type: str) -> str:
        """Enregistre le fichier sous `key` et renvoie son URL https publique."""
        ...

    def delete(self, url: str) -> None:
        """Supprime le fichier désigné par `url` (sans erreur s'il n'existe pas)."""
        ...


class DisabledStorage:
    def save(self, key: str, data: bytes, content_type: str) -> str:
        raise ServiceUnavailable(
            "image_storage_not_configured",
            "Le téléversement d'images n'est pas encore activé (aucun stockage persistant configuré). "
            "Utiliser une URL https en attendant.",
        )

    def delete(self, url: str) -> None:
        return None


class MemoryStorage:
    """Pour les tests seulement (interdit en production par la configuration)."""

    BASE_URL = "https://images.test.invalid/"

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def save(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = (data, content_type)
        return self.BASE_URL + key

    def delete(self, url: str) -> None:
        if url.startswith(self.BASE_URL):
            self.objects.pop(url.removeprefix(self.BASE_URL), None)


@lru_cache
def get_image_storage() -> ImageStorage:
    backend = get_settings().effective_image_storage_backend
    if backend == "memory":
        return MemoryStorage()
    return DisabledStorage()
