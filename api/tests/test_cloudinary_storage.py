"""Adaptateur Cloudinary (ADR-009) : signature, envoi, URL, suppression, erreurs, configuration.

Aucun appel réseau : `urllib.request.urlopen` est remplacé. Les identifiants sont générés à l'exécution.
"""

import io
import json
import secrets
import urllib.error

import pytest

from app.core.config import Settings
from app.core.errors import ServiceUnavailable
from app.services import image_storage
from app.services.image_storage import CloudinaryStorage, cloudinary_signature

CLOUD = "ql-demo"
FOLDER = "quincaillerie-laurentienne"


@pytest.fixture
def creds():
    return {"api_key": secrets.token_hex(8), "api_secret": secrets.token_urlsafe(24)}


@pytest.fixture
def storage(creds):
    return CloudinaryStorage(CLOUD, creds["api_key"], creds["api_secret"], FOLDER)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Calls(list):
    """Requêtes enregistrées ; `reply` est la réponse (dict JSON) ou l'exception à lever."""

    reply: object = {}

    def set_reply(self, reply: object) -> None:
        self.reply = reply


@pytest.fixture
def calls(monkeypatch):
    recorded = Calls()

    def fake_urlopen(request, timeout):
        recorded.append(request)
        if isinstance(recorded.reply, Exception):
            raise recorded.reply
        return FakeResponse(json.dumps(recorded.reply).encode())

    monkeypatch.setattr(image_storage.urllib.request, "urlopen", fake_urlopen)
    return recorded


def test_signature_matches_the_cloudinary_documentation_example():
    # Exemple officiel (SHA-1) : timestamp=1315060510, secret « abcd ».
    assert cloudinary_signature({"timestamp": "1315060510"}, "abcd", "sha1") == (
        "a21ad0f63beb4de2e5575204b79ab90bffb02c10"
    )
    params = {
        "eager": "w_400,h_300,c_pad|w_260,h_200,c_crop",
        "public_id": "sample_image",
        "timestamp": "1315060510",
    }
    assert cloudinary_signature(params, "abcd", "sha1") == "bfd09f95f331f558cbd1320e67aa8d488770583e"


def test_signature_excludes_file_api_key_cloud_name_and_resource_type():
    base = {"public_id": "x", "timestamp": "1"}
    noisy = {**base, "file": "...", "api_key": "k", "cloud_name": "c", "resource_type": "image"}
    assert cloudinary_signature(noisy, "s") == cloudinary_signature(base, "s")
    assert len(cloudinary_signature(base, "s")) == 64  # SHA-256 en production


def test_upload_sends_a_signed_multipart_request_and_returns_the_secure_url(storage, creds, calls):
    url = f"https://res.cloudinary.com/{CLOUD}/image/upload/v17/{FOLDER}/products/p1/abc.png"
    calls.set_reply({"secure_url": url, "public_id": f"{FOLDER}/products/p1/abc"})
    assert storage.save("products/p1/abc.png", b"\x89PNG-octets", "image/png") == url
    [request] = calls
    assert request.full_url == f"https://api.cloudinary.com/v1_1/{CLOUD}/image/upload"
    assert request.get_method() == "POST"
    assert request.headers["Content-type"].startswith("multipart/form-data; boundary=")
    body = request.data
    assert b"\x89PNG-octets" in body and b"Content-Type: image/png" in body
    assert f'name="public_id"\r\n\r\n{FOLDER}/products/p1/abc\r\n'.encode() in body
    assert b'name="allowed_formats"\r\n\r\njpg,png,webp\r\n' in body
    assert b'name="overwrite"\r\n\r\nfalse\r\n' in body
    assert creds["api_key"].encode() in body  # envoyée, mais jamais signée
    assert creds["api_secret"].encode() not in body  # le secret ne quitte jamais l'API


@pytest.mark.parametrize(
    "reply",
    [
        {},
        {"secure_url": "http://res.cloudinary.com/ql-demo/image/upload/x.png"},
        {"secure_url": "https://res.cloudinary.com/autre-compte/image/upload/x.png"},
        {"secure_url": "https://pirate.example/x.png"},
    ],
)
def test_unexpected_responses_are_refused(storage, calls, reply):
    calls.set_reply(reply)
    with pytest.raises(ServiceUnavailable) as exc:
        storage.save("products/p1/abc.png", b"x", "image/png")
    assert exc.value.code == "image_storage_unavailable"


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError("https://api.cloudinary.com", 401, "Unauthorized", {}, None),
        urllib.error.URLError("dns"),
        TimeoutError(),
    ],
)
def test_provider_errors_become_503_without_leaking_secrets(storage, creds, calls, caplog, error):
    calls.set_reply(error)
    with pytest.raises(ServiceUnavailable) as exc:
        storage.save("products/p1/abc.png", b"x", "image/png")
    assert exc.value.code == "image_storage_unavailable"
    text = exc.value.message + caplog.text
    assert creds["api_secret"] not in text and creds["api_key"] not in text


def test_public_id_is_extracted_only_from_our_own_cloudinary_urls(storage):
    own = f"https://res.cloudinary.com/{CLOUD}/image/upload/v1712/{FOLDER}/products/p1/abc.webp"
    assert storage.public_id_from_url(own) == f"{FOLDER}/products/p1/abc"
    assert storage.public_id_from_url("https://images.example.com/abc.jpg") is None
    assert storage.public_id_from_url(f"https://res.cloudinary.com/autre/image/upload/{FOLDER}/a.png") is None
    assert (
        storage.public_id_from_url(f"https://res.cloudinary.com/{CLOUD}/image/upload/autre-dossier/a.png")
        is None
    )
    assert (
        storage.public_id_from_url(f"https://res.cloudinary.com/{CLOUD}/image/upload/{FOLDER}/../a.png")
        is None
    )


def test_delete_sends_a_signed_destroy_request(storage, creds, calls):
    calls.set_reply({"result": "ok"})
    storage.delete(f"https://res.cloudinary.com/{CLOUD}/image/upload/v1/{FOLDER}/products/p1/abc.png")
    [request] = calls
    assert request.full_url == f"https://api.cloudinary.com/v1_1/{CLOUD}/image/destroy"
    body = request.data.decode()
    assert "public_id=quincaillerie-laurentienne%2Fproducts%2Fp1%2Fabc" in body
    assert "invalidate=true" in body and "signature=" in body
    assert creds["api_secret"] not in body


def test_delete_ignores_external_urls_and_never_raises(storage, calls, caplog):
    storage.delete("https://images.example.com/abc.jpg")
    assert calls == []
    calls.set_reply(urllib.error.URLError("panne"))
    storage.delete(f"https://res.cloudinary.com/{CLOUD}/image/upload/{FOLDER}/products/p1/abc.png")
    assert "suppression non confirmée" in caplog.text


def _prod(**overrides):
    values = {
        "app_env": "production",
        "secret_key": "x" * 40,
        "email_backend": "disabled",
        "cors_origins": "https://exemple.vercel.app",
        "image_storage_backend": "cloudinary",
        "cloudinary_cloud_name": CLOUD,
        "cloudinary_api_key": "k" * 15,
        "cloudinary_api_secret": "s" * 27,
    }
    return Settings(**(values | overrides))


def test_cloudinary_is_allowed_in_production_with_complete_settings():
    assert _prod().effective_image_storage_backend == "cloudinary"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"cloudinary_cloud_name": ""}, "CLOUDINARY_CLOUD_NAME"),
        ({"cloudinary_cloud_name": "Nom Invalide"}, "CLOUDINARY_CLOUD_NAME"),
        ({"cloudinary_api_key": None}, "CLOUDINARY_API_KEY"),
        ({"cloudinary_api_secret": " "}, "CLOUDINARY_API_SECRET"),
        ({"cloudinary_folder": "../x"}, "CLOUDINARY_FOLDER"),
    ],
)
def test_incomplete_cloudinary_settings_prevent_startup(overrides, message):
    with pytest.raises(ValueError, match=message):
        _prod(**overrides)


def test_factory_builds_the_cloudinary_adapter(monkeypatch):
    monkeypatch.setattr(image_storage, "get_settings", lambda: _prod())
    image_storage.get_image_storage.cache_clear()
    try:
        adapter = image_storage.get_image_storage()
        assert isinstance(adapter, CloudinaryStorage) and adapter.cloud_name == CLOUD
    finally:
        image_storage.get_image_storage.cache_clear()
