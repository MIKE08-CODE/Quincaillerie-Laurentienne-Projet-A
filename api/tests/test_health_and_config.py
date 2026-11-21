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
