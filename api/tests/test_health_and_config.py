import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE = {"database_url": "postgresql+psycopg://x:y@localhost/z", "mfa_encryption_key": "k"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers


def test_production_refuses_placeholder_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key="change-me", **BASE)


def test_production_refuses_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS"):
        Settings(app_env="production", secret_key="x" * 40, cors_origins="*", **BASE)


def test_access_token_lifetime_cannot_exceed_15_minutes():
    with pytest.raises(ValidationError):
        Settings(secret_key="x" * 40, access_token_expire_minutes=60, **BASE)


SECRETS = {
    "database_url": "postgresql+psycopg://u:MOT-DE-PASSE-BASE@localhost/z",
    "cloudinary_api_key": "1234567",
    "brevo_api_key": "brevo-zz8",
    "cloudinary_api_secret": "cld-zz9",  # dernière valeur : celle que Pydantic recopiait en fin de message
}


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"cloudinary_cloud_name": "Nom-Invalide"}, "CLOUDINARY_CLOUD_NAME"),  # erreur du modèle
        ({"cloudinary_folder": "dossier/invalide"}, "CLOUDINARY_FOLDER"),
        ({"image_storage_backend": "Cloudinary"}, "image_storage_backend"),  # erreur d'un champ
    ],
)
def test_configuration_errors_never_echo_secrets(overrides, expected):
    """Un démarrage refusé écrit l'erreur dans les journaux de Render : aucun secret ne doit y figurer."""
    values = {
        "app_env": "production",
        "secret_key": "CLE-DE-SIGNATURE-FICTIVE-" + "x" * 32,
        "mfa_encryption_key": "k",
        "cors_origins": "https://exemple.test",
        "email_backend": "brevo",
        "email_from_address": "expediteur@exemple.test",
        "image_storage_backend": "cloudinary",
        "cloudinary_cloud_name": "demo-cloud",
        **SECRETS,
    } | overrides
    with pytest.raises(ValidationError) as excinfo:
        Settings(**values)
    message = str(excinfo.value)
    assert expected in message  # la cause reste explicite
    assert "input_value" not in message  # aucune valeur reçue n'est recopiée
    for secret in [*SECRETS.values(), values["secret_key"], "MOT-DE-PASSE-BASE"]:
        assert secret not in message
