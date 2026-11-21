"""F1 — Envoi des courriels : modes, robustesse et confidentialité (A-AUTH-01, A-AUTH-04, ENF-13)."""

import io
import json
import logging
import secrets
import urllib.error

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings
from app.services import email_service

TOKEN = secrets.token_urlsafe(24)  # jeton aléatoire, généré à chaque exécution des tests


def _settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "secret_key": secrets.token_urlsafe(48),
        "database_url": "postgresql+psycopg://u:p@localhost/db",
        "mfa_encryption_key": "x" * 44,
        "cors_origins": "https://ql.example",
    } | overrides
    return Settings(_env_file=None, **values)


@pytest.fixture
def backend(monkeypatch):
    """Change le mode d'envoi de la configuration partagée le temps d'un test."""

    def _set(name: str, **extra):
        settings = get_settings()
        monkeypatch.setattr(settings, "email_backend", name)
        for key, value in extra.items():
            monkeypatch.setattr(settings, key, value)

    return _set


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_default_backend_depends_on_environment():
    assert _settings(app_env="development").effective_email_backend == "console"
    assert _settings(app_env="test").effective_email_backend == "memory"
    assert _settings(app_env="production").effective_email_backend == "disabled"


@pytest.mark.parametrize("name", ["console", "memory"])
def test_console_and_memory_backends_are_refused_in_production(name):
    with pytest.raises(ValidationError, match="interdit en production"):
        _settings(email_backend=name)


def test_brevo_requires_an_api_key_and_a_sender():
    with pytest.raises(ValidationError, match="BREVO_API_KEY"):
        _settings(email_backend="brevo", email_from_address="ql@example.com")
    with pytest.raises(ValidationError, match="EMAIL_FROM_ADDRESS"):
        _settings(email_backend="brevo", brevo_api_key="cle")
    ok = _settings(email_backend="brevo", brevo_api_key="cle", email_from_address="ql@example.com")
    assert ok.effective_email_backend == "brevo"


# ---------------------------------------------------------------------------
# Mode « disabled » : aucun envoi, aucune exception, aucun secret journalisé
# ---------------------------------------------------------------------------
def test_disabled_backend_does_not_raise_and_logs_without_secrets(backend, caplog):
    backend("disabled")
    with caplog.at_level(logging.WARNING, logger="app.email"):
        sent = email_service.send_verification_email("marie@example.com", "fr", TOKEN)
    assert sent is False
    assert "non envoyé" in caplog.text and "verify" in caplog.text
    for secret in (TOKEN, "#token=", "marie@example.com", "verifier-courriel"):
        assert secret not in caplog.text


def test_registration_still_answers_and_the_connection_survives(client, backend, caplog):
    """Avant F1 : la tâche d'arrière-plan levait NotImplementedError et coupait la connexion."""
    backend("disabled")
    payload = {
        "email": "nouveau@example.com",
        "password": "Rivière-Pelle-Écrou-42",
        "first_name": "Nouveau",
        "last_name": "Client",
        "language": "fr",
        "accept_privacy_policy": True,
    }
    with caplog.at_level(logging.WARNING, logger="app.email"):
        response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 202
    assert client.get("/health").status_code == 200  # même client, connexion toujours utilisable
    assert "#token=" not in caplog.text


# ---------------------------------------------------------------------------
# Mode « brevo » : appel HTTPS du fournisseur
# ---------------------------------------------------------------------------
class _FakeResponse(io.BytesIO):
    def __init__(self, status: int):
        super().__init__(b"{}")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_brevo_sends_the_message_over_https(backend, monkeypatch):
    backend("brevo", brevo_api_key=SecretStr("cle-de-test"), email_from_address="ql@example.com")
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return _FakeResponse(201)

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)
    assert email_service.send_password_reset_email("marie@example.com", "en", TOKEN) is True
    [(request, timeout)] = calls
    assert request.full_url == "https://api.brevo.com/v3/smtp/email"
    assert request.get_method() == "POST" and timeout == email_service.SEND_TIMEOUT_SECONDS
    assert request.get_header("Api-key") == "cle-de-test"
    body = json.loads(request.data)
    assert body["to"] == [{"email": "marie@example.com"}]
    assert body["sender"]["email"] == "ql@example.com"
    assert body["subject"] == "Password reset" and f"#token={TOKEN}" in body["textContent"]


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://api.brevo.com", 401, "Unauthorized", {}, None),
        urllib.error.URLError("nom introuvable"),
        TimeoutError("délai dépassé"),
        RuntimeError("imprévu"),
    ],
)
def test_brevo_failures_never_raise_nor_leak(backend, monkeypatch, caplog, failure):
    backend("brevo", brevo_api_key=SecretStr("cle-de-test"), email_from_address="ql@example.com")

    def fake_urlopen(request, timeout):
        raise failure

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)
    with caplog.at_level(logging.ERROR, logger="app.email"):
        assert email_service.send_verification_email("marie@example.com", "fr", TOKEN) is False
    assert "Échec" in caplog.text
    for secret in (TOKEN, "#token=", "marie@example.com", "cle-de-test"):
        assert secret not in caplog.text


def test_brevo_unexpected_status_is_an_error(backend, monkeypatch, caplog):
    backend("brevo", brevo_api_key=SecretStr("cle-de-test"), email_from_address="ql@example.com")
    monkeypatch.setattr(email_service.urllib.request, "urlopen", lambda request, timeout: _FakeResponse(500))
    with caplog.at_level(logging.ERROR, logger="app.email"):
        assert email_service.send_already_registered_email("marie@example.com", "fr") is False
    assert "HTTP 500" in caplog.text
