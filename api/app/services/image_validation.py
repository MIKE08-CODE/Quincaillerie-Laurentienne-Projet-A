"""Validation des images téléversées (A-ADM-01 : « validation du type et de la taille »).

Le type est déduit des OCTETS du fichier (signature), jamais du nom ni de l'en-tête `Content-Type`
envoyé par le client, qui peuvent mentir. Seuls JPEG, PNG et WebP sont acceptés : SVG (peut contenir
du script), GIF, HTML, PDF et exécutables sont refusés. Les dimensions sont lues dans l'en-tête de
l'image pour refuser les « bombes de décompression » (image minuscule sur disque, énorme en mémoire)
avant tout traitement. Aucune bibliothèque de décodage n'est utilisée : rien n'est décodé.
"""

import struct
from dataclasses import dataclass

from app.core.errors import PayloadTooLarge, UnsupportedMediaType, ValidationFailed


@dataclass(frozen=True)
class ImageInfo:
    content_type: str
    extension: str
    width: int
    height: int


_ALLOWED_DECLARED = {"image/jpeg", "image/png", "image/webp"}


def _png_size(data: bytes) -> tuple[int, int]:
    # Signature (8) + longueur (4) + « IHDR » (4) + largeur (4) + hauteur (4)
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise ValidationFailed("image_invalid", "Fichier PNG illisible.")
    return struct.unpack(">II", data[16:24])


def _webp_size(data: bytes) -> tuple[int, int]:
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 30:  # avec perte
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:  # sans perte
        b = data[21:25]
        w = 1 + (((b[1] & 0x3F) << 8) | b[0])
        h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        return w, h
    if chunk == b"VP8X" and len(data) >= 30:  # étendu
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    raise ValidationFailed("image_invalid", "Fichier WebP illisible.")


# Marqueurs JPEG « Start Of Frame » portant les dimensions (sauf DHT C4, JPG C8, DAC CC).
_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _jpeg_size(data: bytes) -> tuple[int, int]:
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xFF:  # octet de remplissage
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:  # marqueurs sans longueur
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if length < 2:
            break
        if marker in _SOF_MARKERS:
            if i + 9 > len(data):
                break
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        i += 2 + length
    raise ValidationFailed("image_invalid", "Fichier JPEG illisible.")


def detect(data: bytes) -> tuple[str, str]:
    """Type réel (content-type, extension) d'après la signature, ou erreur 415."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise UnsupportedMediaType(
        "unsupported_image_type", "Format refusé : seules les images JPEG, PNG et WebP sont acceptées."
    )


def validate_image(
    data: bytes, *, declared_type: str | None, max_bytes: int, max_dimension: int
) -> ImageInfo:
    """Vérifie taille, type réel, cohérence avec le type déclaré et dimensions."""
    if not data:
        raise ValidationFailed("image_empty", "Le fichier est vide.")
    if len(data) > max_bytes:
        raise PayloadTooLarge("image_too_large", f"Image trop lourde (maximum {max_bytes // 1024} Kio).")
    content_type, extension = detect(data)
    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared not in _ALLOWED_DECLARED:
        raise UnsupportedMediaType(
            "unsupported_image_type", "En-tête Content-Type attendu : image/jpeg, image/png ou image/webp."
        )
    if declared != content_type:
        raise UnsupportedMediaType(
            "image_type_mismatch", "Le contenu du fichier ne correspond pas au type déclaré."
        )
    reader = {"image/png": _png_size, "image/webp": _webp_size, "image/jpeg": _jpeg_size}[content_type]
    width, height = reader(data)
    if width <= 0 or height <= 0:
        raise ValidationFailed("image_invalid", "Dimensions de l'image invalides.")
    if width > max_dimension or height > max_dimension:
        raise ValidationFailed(
            "image_dimensions_too_large", f"Image trop grande (maximum {max_dimension} pixels par côté)."
        )
    return ImageInfo(content_type, extension, width, height)
