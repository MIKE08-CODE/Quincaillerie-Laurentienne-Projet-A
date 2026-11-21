"""Tests des protections ajoutées lors de la revue de sécurité (annexe D, OWASP Top 10).

Chaque test correspond à un problème réel constaté pendant la revue : s'il échoue, la faille revient.
"""

import logging
import unicodedata
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core import security
from app.models import RefreshToken, UserRole
from app.services import auth_service
from tests.conftest import PASSWORD, auth_header, last_email_token

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"


# --- A-AUTH-03 : aucun mot de passe en clair dans les réponses ---
def test_validation_error_never_echoes_the_password(client):
    """Avant : une erreur 422 recopiait le mot de passe trop long dans la réponse."""
    secret = "MonSecret-" + "x" * 1100
    response = client.post(LOGIN, json={"email": "a@example.com", "password": secret})
    assert response.status_code == 422
    assert "MonSecret" not in response.text
    assert response.json()["detail"]["code"] == "validation_error"
    assert response.json()["detail"]["errors"][0]["field"] == "body.password"


def test_unknown_field_value_is_not_echoed(client):
    response = client.post(LOGIN, json={"email": "a@example.com", "password": "x", "role": "admin-secret"})
    assert response.status_code == 422
    assert "admin-secret" not in response.text


# --- A-AUTH-03 : le mot de passe n'est jamais modifié en silence ---
def test_spaces_in_password_are_kept(client, make_user):
    """Avant : « secret  » devenait « secret ». Les espaces font partie du mot de passe."""
    user = make_user(password="  Espaces-Avant-Et-Apres  ")
    trimmed = client.post(LOGIN, json={"email": user.email, "password": "Espaces-Avant-Et-Apres"})
    exact = client.post(LOGIN, json={"email": user.email, "password": "  Espaces-Avant-Et-Apres  "})
    assert trimmed.status_code == 401
    assert exact.status_code == 200


def test_accented_password_works_from_any_device(client, make_user):
    """« é » composé (Windows) ou décomposé (macOS) : c'est le même mot de passe (NFKC)."""
    user = make_user(password=unicodedata.normalize("NFC", PASSWORD))
    decomposed = unicodedata.normalize("NFD", PASSWORD)
    assert decomposed != PASSWORD
    assert client.post(LOGIN, json={"email": user.email, "password": decomposed}).status_code == 200


# --- A-AUTH-01 : pas d'énumération par le temps de réponse ---
def test_register_hashes_password_even_when_email_exists(client, make_user, monkeypatch):
    """Avant : 15 ms si le courriel existait, 156 ms sinon (Argon2 sauté). On vérifie que le
    hachage, l'opération lente, est effectué dans les deux cas."""
    user = make_user()
    calls = []
    original = security.hash_password
    monkeypatch.setattr(security, "hash_password", lambda p: calls.append(1) or original(p))

    body = {"password": PASSWORD, "first_name": "A", "last_name": "B", "accept_privacy_policy": True}
    client.post(REGISTER, json={"email": user.email, **body})
    client.post(REGISTER, json={"email": "nouveau@example.com", **body})
    assert len(calls) == 2


# --- ENF-03 / OWASP : réponses jamais mises en cache ---
def test_auth_responses_are_not_cacheable(client, make_user):
    user = make_user()
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert response.headers["Cache-Control"] == "no-store"


# --- OWASP A07 : jetons volés invalidés par une réinitialisation ---
def test_access_token_issued_before_password_reset_is_rejected(client, db, make_user):
    user = make_user()
    old_headers = auth_header(user)
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 200

    # Le jeton est émis dans la seconde précédente : on recule son émission d'une seconde.
    old_token = security.create_jwt(user.id, "access", timedelta(minutes=15), mfa=False)
    client.post("/api/v1/auth/password/forgot", json={"email": user.email})
    db.refresh(user)
    client.post(
        "/api/v1/auth/password/reset",
        json={"token": last_email_token(), "new_password": "Nouveau-Tournevis-Étoile-77"},
    )
    db.refresh(user)
    user.tokens_valid_after = datetime.now(UTC) + timedelta(seconds=1)  # garantit « émis avant »
    db.commit()

    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_new_login_after_password_reset_works(client, make_user):
    user = make_user()
    client.post("/api/v1/auth/password/forgot", json={"email": user.email})
    new_password = "Nouveau-Tournevis-Étoile-77"
    client.post(
        "/api/v1/auth/password/reset", json={"token": last_email_token(), "new_password": new_password}
    )
    token = client.post(LOGIN, json={"email": user.email, "password": new_password}).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# --- OWASP A07 : durée maximale d'une session ---
def test_session_cannot_be_extended_forever(client, db, make_user):
    user = make_user()
    client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    first = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)).one()
    session_end = first.session_expires_at

    assert client.post("/api/v1/auth/refresh").status_code == 200
    rotated = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).one()
    assert rotated.session_expires_at == session_end  # recopiée, pas prolongée

    # Fin absolue atteinte : le rafraîchissement est refusé même si le jeton lui-même est valide.
    rotated.session_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    rotated.expires_at = rotated.session_expires_at
    db.commit()
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_session_lasts_at_most_30_days(client, db, make_user):
    user = make_user()
    client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    token = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)).one()
    assert token.session_expires_at - token.created_at <= timedelta(days=30, seconds=5)
    assert token.expires_at <= token.session_expires_at


# --- A-AUTH-06/07 : les codes MFA comptent dans le verrouillage, même à l'activation ---
def test_wrong_codes_at_mfa_enable_lock_the_account(client, make_user):
    """Avant : /mfa/enable acceptait un nombre illimité d'essais par compte."""
    user = make_user(UserRole.CLERK)
    limited = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()["access_token"]
    headers = {"Authorization": f"Bearer {limited}"}
    client.post("/api/v1/auth/mfa/setup", headers=headers)
    for _ in range(5):
        client.post("/api/v1/auth/mfa/enable", headers=headers, json={"code": "000000"})
    assert client.post("/api/v1/auth/mfa/enable", headers=headers, json={"code": "000000"}).status_code == 423


def test_mfa_challenge_from_before_password_reset_is_rejected(db, make_user):
    user = make_user(UserRole.ADMIN)
    user.mfa_enabled = True
    user.tokens_valid_after = datetime.now(UTC) + timedelta(seconds=1)
    db.commit()
    challenge = security.create_mfa_challenge_token(user.id)
    payload = security.decode_jwt(challenge, "mfa_challenge")
    assert security.issued_before(payload, user.tokens_valid_after)


# --- Annexe D, A09 : journalisation des événements de sécurité, sans renseignements personnels ---
def test_security_events_are_logged_without_personal_data(client, make_user, caplog):
    caplog.set_level(logging.INFO, logger="app.security")
    user = make_user(email="personne.privee@example.com")
    for _ in range(5):
        client.post(LOGIN, json={"email": user.email, "password": "Mauvais-mot-de-passe-1"})

    assert "event=login_failed" in caplog.text
    assert "event=account_locked" in caplog.text
    assert str(user.id) in caplog.text  # identifiant interne : permet d'enquêter
    assert "personne.privee" not in caplog.text  # mais pas le courriel (Loi 25, ENF-13)
    assert "Mauvais-mot-de-passe" not in caplog.text


def test_refresh_token_theft_is_logged(client, make_user, caplog):
    caplog.set_level(logging.WARNING, logger="app.security")
    user = make_user()
    client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    stolen = client.cookies.get("ql_refresh")
    client.post("/api/v1/auth/refresh")
    client.cookies.set("ql_refresh", stolen, path="/api/v1/auth")
    client.post("/api/v1/auth/refresh")
    assert "event=refresh_token_reuse_detected" in caplog.text


def test_auth_service_never_trusts_a_role_from_outside():
    """register() n'a pas de paramètre de rôle : impossible de s'inscrire autrement que client."""
    import inspect

    assert "role" not in inspect.signature(auth_service.register).parameters
