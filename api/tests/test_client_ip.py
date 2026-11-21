"""F2 — Adresse du client pour la limitation de débit (ENF-05).

Aucun en-tête de proxy n'est cru par défaut.
"""

import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings

LOGIN = "/api/v1/auth/login"
BAD_LOGIN = {"email": "inconnu@example.com", "password": "mauvais-mot-de-passe"}  # nosec B105


def _logins(client, headers_list):
    return [client.post(LOGIN, json=BAD_LOGIN, headers=h).status_code for h in headers_list]


@pytest.fixture
def trusted_header(monkeypatch):
    def _set(name: str):
        monkeypatch.setattr(get_settings(), "client_ip_header", name)

    return _set


@pytest.mark.parametrize(
    "header", ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP", "True-Client-IP", "Forwarded"]
)
def test_spoofed_proxy_headers_do_not_bypass_the_limit_by_default(client, header):
    """Avant F2 : avec --forwarded-allow-ips='*', un X-Forwarded-For inventé donnait un nouveau compteur."""
    value = (lambda i: f"for=203.0.113.{i}") if header == "Forwarded" else (lambda i: f"203.0.113.{i}")
    codes = _logins(client, [{header: value(i)} for i in range(1, 12)])
    assert codes[:10] == [401] * 10
    assert codes[10] == 429  # la 11e tentative est bloquée malgré un en-tête différent à chaque fois


def test_configured_header_identifies_clients_set_by_the_trusted_edge(client, trusted_header):
    trusted_header("cf-connecting-ip")
    # Deux clients distincts selon le relais de confiance : compteurs séparés.
    first = _logins(client, [{"CF-Connecting-IP": "198.51.100.1"}] * 10)
    second = _logins(client, [{"CF-Connecting-IP": "198.51.100.2"}] * 10)
    assert first == [401] * 10 and second == [401] * 10
    assert _logins(client, [{"CF-Connecting-IP": "198.51.100.1"}]) == [429]


def test_configured_header_ignores_x_forwarded_for(client, trusted_header):
    trusted_header("cf-connecting-ip")
    headers = [
        {"CF-Connecting-IP": "198.51.100.9", "X-Forwarded-For": f"203.0.113.{i}"} for i in range(1, 12)
    ]
    assert _logins(client, headers)[-1] == 429


@pytest.mark.parametrize(
    "bad_value", ["", "pas-une-ip", "198.51.100.1, 203.0.113.5", "999.1.1.1", "<script>"]
)
def test_invalid_header_values_fall_back_to_the_connection_address(client, trusted_header, bad_value):
    """Une valeur absente ou invalide n'ouvre pas de nouveau compteur : retour à l'adresse de connexion."""
    trusted_header("cf-connecting-ip")
    codes = _logins(
        client, [{"CF-Connecting-IP": f"{bad_value}{'x' * i if bad_value else ''}"} for i in range(11)]
    )
    assert codes[-1] == 429


def _settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "secret_key": secrets.token_urlsafe(48),
        "database_url": "postgresql+psycopg://u:p@localhost/db",
        "mfa_encryption_key": "x" * 44,
        "cors_origins": "https://ql.example",
    } | overrides
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("header", ["X-Forwarded-For", "x-forwarded-for", "Forwarded"])
def test_x_forwarded_for_cannot_be_configured(header):
    with pytest.raises(ValidationError, match="falsifiables"):
        _settings(client_ip_header=header)


def test_header_name_is_validated_and_normalized():
    with pytest.raises(ValidationError):
        _settings(client_ip_header="cf connecting ip")
    assert _settings(client_ip_header="CF-Connecting-IP").client_ip_header == "cf-connecting-ip"
    assert _settings().client_ip_header == ""
