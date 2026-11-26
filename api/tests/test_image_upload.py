"""Téléversement d'images de produits (A-ADM-01 : validation du type et de la taille)."""

import struct
import zlib

import pytest

from app.core.config import Settings, get_settings
from app.core.errors import PayloadTooLarge, UnsupportedMediaType, ValidationFailed
from app.main import app
from app.models import UserRole
from app.services import image_validation
from app.services.image_storage import DisabledStorage, MemoryStorage, get_image_storage
from tests.conftest import auth_header, error_code

API = "/api/v1/admin/products"


# ---------------------------------------------------------------------------
# Fabriques d'images minimales (octets réels, aucun fichier dans le dépôt)
# ---------------------------------------------------------------------------
def png(width: int = 2, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(min(height, 4)))
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


def jpeg(width: int = 2, height: int = 2) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def webp(width: int = 2, height: int = 2) -> bytes:
    vp8x = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00"
    vp8x += (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(vp8x)) + b"WEBP" + vp8x


# ---------------------------------------------------------------------------
# Validation (unitaire)
# ---------------------------------------------------------------------------
LIMITS = {"max_bytes": 5 * 1024 * 1024, "max_dimension": 6000}


@pytest.mark.parametrize(
    ("data", "declared", "expected"),
    [
        (png(), "image/png", "image/png"),
        (jpeg(), "image/jpeg", "image/jpeg"),
        (webp(), "image/webp", "image/webp"),
    ],
)
def test_accepts_real_jpeg_png_webp(data, declared, expected):
    info = image_validation.validate_image(data, declared_type=declared, **LIMITS)
    assert info.content_type == expected and (info.width, info.height) == (2, 2)


@pytest.mark.parametrize(
    "data",
    [
        b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"GIF89a\x01\x00\x01\x00",
        b"<html><script>alert(1)</script></html>",
        b"%PDF-1.7",
        b"MZ\x90\x00",  # exécutable Windows
    ],
)
def test_refuses_other_formats_even_if_declared_as_image(data):
    with pytest.raises(UnsupportedMediaType) as exc:
        image_validation.validate_image(data, declared_type="image/png", **LIMITS)
    assert exc.value.code == "unsupported_image_type"


def test_refuses_content_that_does_not_match_the_declared_type():
    with pytest.raises(UnsupportedMediaType) as exc:
        image_validation.validate_image(png(), declared_type="image/jpeg", **LIMITS)
    assert exc.value.code == "image_type_mismatch"


def test_refuses_missing_or_non_image_declared_type():
    for declared in (None, "", "application/octet-stream", "image/svg+xml"):
        with pytest.raises(UnsupportedMediaType):
            image_validation.validate_image(png(), declared_type=declared, **LIMITS)


def test_refuses_empty_and_oversized_files():
    with pytest.raises(ValidationFailed):
        image_validation.validate_image(b"", declared_type="image/png", **LIMITS)
    with pytest.raises(PayloadTooLarge):
        image_validation.validate_image(png(), declared_type="image/png", max_bytes=10, max_dimension=6000)


@pytest.mark.parametrize("factory", [png, jpeg, webp])
def test_refuses_decompression_bombs_by_reading_dimensions(factory):
    with pytest.raises(ValidationFailed) as exc:
        image_validation.validate_image(
            factory(9000, 9000), declared_type=f"image/{factory.__name__}", **LIMITS
        )
    assert exc.value.code == "image_dimensions_too_large"


@pytest.mark.parametrize(
    ("data", "declared"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 4, "image/png"),
        (b"\xff\xd8\xff\xe0\x00", "image/jpeg"),
        (b"RIFF\x00\x00\x00\x00WEBPXXXX", "image/webp"),
    ],
)
def test_refuses_truncated_files(data, declared):
    with pytest.raises(ValidationFailed) as exc:
        image_validation.validate_image(data, declared_type=declared, **LIMITS)
    assert exc.value.code == "image_invalid"


# ---------------------------------------------------------------------------
# Route d'API
# ---------------------------------------------------------------------------
@pytest.fixture
def storage():
    """Stockage en mémoire neuf pour chaque test."""
    memory = MemoryStorage()
    app.dependency_overrides[get_image_storage] = lambda: memory
    yield memory
    app.dependency_overrides.pop(get_image_storage, None)


@pytest.fixture
def product(make_product):
    return make_product("PERC-18V-UP")


def _upload(client, product_id, data, content_type, headers, **params):
    return client.post(
        f"{API}/{product_id}/images/upload",
        content=data,
        headers={**headers, "Content-Type": content_type},
        params=params,
    )


def test_admin_uploads_an_image_and_it_is_attached_to_the_product(client, admin_headers, product, storage):
    response = _upload(
        client, product.id, png(), "image/png", admin_headers, alt_fr="Perceuse", alt_en="Drill"
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["url"].startswith("https://") and body["url"].endswith(".png")
    assert body["alt_fr"] == "Perceuse" and body["position"] == 0
    [(key, (data, content_type))] = storage.objects.items()
    assert key.startswith(f"products/{product.id}/") and data == png() and content_type == "image/png"
    detail = client.get(f"{API}/{product.id}", headers=admin_headers).json()
    assert [i["url"] for i in detail["images"]] == [body["url"]]


def test_server_generates_the_file_name(client, admin_headers, product, storage):
    first = _upload(client, product.id, jpeg(), "image/jpeg", admin_headers).json()
    second = _upload(client, product.id, jpeg(), "image/jpeg", admin_headers).json()
    assert first["url"] != second["url"] and second["position"] == 0  # la plus récente est la principale
    assert all(".." not in key and "/" in key for key in storage.objects)


PLACEHOLDER = "https://images.quincaillerie-laurentienne.example/products/perc-18v-up.jpg"


def test_uploaded_image_is_shown_by_the_public_catalog(client, admin_headers, product, storage):
    """Parcours complet (issue #10) : téléversement → enregistrement du formulaire → catalogue public.

    En production, chaque produit amorcé a déjà une image de remplacement en position 0 (domaine
    `.example`, jamais résolu). L'image téléversée doit devenir l'image principale de la carte et de
    la fiche, sans supprimer l'image existante.
    """
    seeded = client.post(f"{API}/{product.id}/images", json={"url": PLACEHOLDER}, headers=admin_headers)
    assert seeded.status_code == 201 and seeded.json()["position"] == 0

    uploaded = _upload(client, product.id, jpeg(), "image/jpeg", admin_headers, alt_fr="Perceuse").json()
    assert uploaded["position"] == 0  # l'image téléversée devient la principale

    # « Enregistrer » dans /admin (nom, prix, activation) ne touche pas aux images.
    saved = client.patch(
        f"{API}/{product.id}",
        json={"name_fr": "Perceuse 18 V", "name_en": "Drill 18 V", "price_cents": 12999, "is_active": True},
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text

    listing = client.get("/api/v1/products", params={"size": 50}).json()["items"]
    card = next(item for item in listing if item["id"] == str(product.id))
    assert card["main_image_url"] == uploaded["url"]

    detail = client.get(f"/api/v1/products/{product.id}").json()
    assert [(i["url"], i["position"]) for i in detail["images"]] == [(uploaded["url"], 0), (PLACEHOLDER, 1)]


def test_each_new_upload_becomes_the_main_image_and_keeps_the_others(client, admin_headers, product, storage):
    first = _upload(client, product.id, png(), "image/png", admin_headers).json()
    second = _upload(client, product.id, png(), "image/png", admin_headers).json()
    third = _upload(client, product.id, png(), "image/png", admin_headers).json()
    detail = client.get(f"/api/v1/products/{product.id}").json()
    assert [i["url"] for i in detail["images"]] == [third["url"], second["url"], first["url"]]
    assert [i["position"] for i in detail["images"]] == [0, 1, 2]


@pytest.mark.parametrize(
    ("data", "content_type", "status", "code"),
    [
        (b"<svg><script>alert(1)</script></svg>", "image/png", 415, "unsupported_image_type"),
        (png(), "image/jpeg", 415, "image_type_mismatch"),
        (png(), "text/plain", 415, "unsupported_image_type"),
        (b"", "image/png", 422, "image_empty"),
        (png(9000, 10), "image/png", 422, "image_dimensions_too_large"),
    ],
)
def test_invalid_uploads_are_refused_and_nothing_is_stored(
    client, admin_headers, product, storage, data, content_type, status, code
):
    response = _upload(client, product.id, data, content_type, admin_headers)
    assert response.status_code == status and error_code(response) == code
    assert storage.objects == {}


def test_too_large_upload_is_413_and_nothing_is_stored(client, admin_headers, product, storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "image_max_bytes", 10_000)
    response = _upload(client, product.id, png() + b"\x00" * 20_000, "image/png", admin_headers)
    assert response.status_code == 413 and error_code(response) == "image_too_large"
    assert storage.objects == {}


def test_unknown_product_is_404_and_nothing_is_stored(client, admin_headers, storage):
    response = _upload(client, "00000000-0000-4000-8000-000000000000", png(), "image/png", admin_headers)
    assert response.status_code == 404 and storage.objects == {}


def test_upload_requires_an_administrator_with_mfa(client, make_user, make_store, product, storage):
    assert _upload(client, product.id, png(), "image/png", {}).status_code == 401
    for role in (UserRole.CLIENT, UserRole.CLERK, UserRole.MANAGER):
        stores = [make_store()] if role in (UserRole.CLERK, UserRole.MANAGER) else []
        headers = auth_header(make_user(role, stores=stores), mfa=True)
        assert _upload(client, product.id, png(), "image/png", headers).status_code == 403
    no_mfa = auth_header(make_user(UserRole.ADMIN), mfa=False)
    response = _upload(client, product.id, png(), "image/png", no_mfa)
    assert response.status_code == 403 and error_code(response) == "mfa_required"
    assert storage.objects == {}


def test_without_storage_upload_is_503_with_a_clear_code(client, admin_headers, product):
    app.dependency_overrides[get_image_storage] = DisabledStorage
    try:
        response = _upload(client, product.id, png(), "image/png", admin_headers)
    finally:
        app.dependency_overrides.pop(get_image_storage, None)
    assert response.status_code == 503 and error_code(response) == "image_storage_not_configured"


def test_deleting_an_uploaded_image_removes_the_file(client, admin_headers, product, storage):
    image = _upload(client, product.id, webp(), "image/webp", admin_headers).json()
    assert len(storage.objects) == 1
    response = client.delete(f"{API}/{product.id}/images/{image['id']}", headers=admin_headers)
    assert response.status_code == 204 and storage.objects == {}


def test_database_failure_removes_the_stored_file(client, admin_headers, product, storage, monkeypatch):
    from app.services import catalog_admin_service

    def boom(*args, **kwargs):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(catalog_admin_service, "add_image", boom)
    with pytest.raises(RuntimeError):
        _upload(client, product.id, png(), "image/png", admin_headers)
    assert storage.objects == {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_storage_defaults_disabled_outside_tests_and_memory_is_forbidden_in_production():
    assert Settings(app_env="development").effective_image_storage_backend == "disabled"
    with pytest.raises(ValueError, match="IMAGE_STORAGE_BACKEND=memory"):
        Settings(
            app_env="production",
            image_storage_backend="memory",
            secret_key="x" * 40,
            email_backend="disabled",
            cors_origins="https://exemple.vercel.app",
        )
