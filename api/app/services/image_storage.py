"""Stockage persistant des images de produits (A-ADM-01), indépendant du fournisseur.

L'API ne garde AUCUN fichier : ni sur le disque de Render (éphémère, effacé à chaque déploiement), ni
dans PostgreSQL (la base gratuite de Neon est limitée et les images n'y ont pas leur place). Un
fournisseur de stockage d'objets reçoit le fichier et renvoie une URL https publique, enregistrée
dans `product_images.url` comme les images désignées par URL.

Implémentations :
- `DisabledStorage` (défaut hors test) : téléversement refusé avec 503 `image_storage_not_configured`;
- `MemoryStorage` (tests) : garde les octets en mémoire;
- `CloudinaryStorage` (ADR-009, à activer par le responsable) : API HTTPS d'envoi signé de Cloudinary,
  sans SDK ni nouvelle dépendance. Signature SHA-256 des paramètres triés suivis du secret, conforme à
  la documentation « Authentication signatures » de Cloudinary.
"""

import hashlib
import json
import logging
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import ServiceUnavailable

logger = logging.getLogger(__name__)

CLOUDINARY_API = "https://api.cloudinary.com/v1_1"
CLOUDINARY_DELIVERY = "https://res.cloudinary.com"
CLOUDINARY_TIMEOUT_SECONDS = 20
# Ne jamais transmettre ces champs dans la chaîne signée (documentation Cloudinary).
_UNSIGNED_FIELDS = {"file", "cloud_name", "resource_type", "api_key"}


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


def _string_to_sign(params: dict[str, str], api_secret: str) -> str:
    """`nom=valeur` triés par nom, joints par `&`, suivis du secret (documentation de Cloudinary)."""
    payload = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if k not in _UNSIGNED_FIELDS and v != "")
    return payload + api_secret


def cloudinary_signature(params: dict[str, str], api_secret: str) -> str:
    """Signature SHA-256 (hexadécimale) acceptée par Cloudinary ; SHA-1 n'est jamais utilisé."""
    return hashlib.sha256(_string_to_sign(params, api_secret).encode("utf-8")).hexdigest()


def _multipart(fields: dict[str, str], file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"ql-{secrets.token_hex(16)}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="image"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode()
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class CloudinaryStorage:
    """Envoi signé vers Cloudinary ; aucun secret n'apparaît dans les erreurs ni les journaux."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str, folder: str) -> None:
        self.cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self.folder = folder
        self.delivery_prefix = f"{CLOUDINARY_DELIVERY}/{cloud_name}/image/upload/"

    def _signed(self, params: dict[str, str]) -> dict[str, str]:
        params = {**params, "timestamp": str(int(time.time()))}
        signature = cloudinary_signature(params, self._api_secret)
        return {**params, "api_key": self._api_key, "signature": signature}

    def _post(self, action: str, body: bytes, content_type: str) -> dict:
        request = urllib.request.Request(  # noqa: S310 — URL https fixe, jamais fournie par l'utilisateur
            f"{CLOUDINARY_API}/{self.cloud_name}/image/{action}",
            data=body,
            headers={"Content-Type": content_type, "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=CLOUDINARY_TIMEOUT_SECONDS) as response:  # noqa: S310  # nosec B310
            return json.loads(response.read().decode("utf-8"))

    def save(self, key: str, data: bytes, content_type: str) -> str:
        public_id = f"{self.folder}/{key.rsplit('.', 1)[0]}"
        fields = self._signed(
            {"public_id": public_id, "overwrite": "false", "allowed_formats": "jpg,png,webp"}
        )
        body, multipart_type = _multipart(fields, data, content_type)
        try:
            result = self._post("upload", body, multipart_type)
        except urllib.error.HTTPError as exc:
            logger.error("Cloudinary : envoi refusé (HTTP %s).", exc.code)
            raise _unavailable() from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            logger.error("Cloudinary : envoi impossible (%s).", type(exc).__name__)
            raise _unavailable() from None
        url = result.get("secure_url") if isinstance(result, dict) else None
        if not isinstance(url, str) or not url.startswith(self.delivery_prefix):
            logger.error("Cloudinary : réponse inattendue (URL absente ou hors du compte configuré).")
            raise _unavailable()
        return url

    def public_id_from_url(self, url: str) -> str | None:
        """`https://res.cloudinary.com/<compte>/image/upload/v123/<public_id>.<ext>` → `<public_id>`."""
        if not url.startswith(self.delivery_prefix):
            return None  # image désignée par une URL externe : rien à supprimer chez Cloudinary
        path = url.removeprefix(self.delivery_prefix)
        path = re.sub(r"^v\d+/", "", path)
        public_id = path.rsplit(".", 1)[0]
        if not public_id.startswith(f"{self.folder}/") or ".." in public_id:
            return None
        return public_id

    def delete(self, url: str) -> None:
        """Suppression au mieux : une erreur est journalisée, jamais propagée (compensation)."""
        public_id = self.public_id_from_url(url)
        if public_id is None:
            return
        fields = self._signed({"public_id": public_id, "invalidate": "true"})
        body = urllib.parse.urlencode(fields).encode("utf-8")
        try:
            self._post("destroy", body, "application/x-www-form-urlencoded")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("Cloudinary : suppression non confirmée (%s).", type(exc).__name__)


def _unavailable() -> ServiceUnavailable:
    return ServiceUnavailable(
        "image_storage_unavailable", "Le stockage des images est momentanément indisponible. Réessayer."
    )


@lru_cache
def get_image_storage() -> ImageStorage:
    settings = get_settings()
    backend = settings.effective_image_storage_backend
    if backend == "memory":
        return MemoryStorage()
    if backend == "cloudinary":
        if settings.cloudinary_api_key is None or settings.cloudinary_api_secret is None:
            return DisabledStorage()  # impossible : la configuration l'interdit déjà
        return CloudinaryStorage(
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key.get_secret_value(),
            settings.cloudinary_api_secret.get_secret_value(),
            settings.cloudinary_folder,
        )
    return DisabledStorage()
