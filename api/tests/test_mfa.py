"""A-AUTH-06 — MFA TOTP obligatoire pour le personnel et les administrateurs.
CA : le personnel ne peut pas accéder aux points de terminaison protégés sans avoir complété la MFA."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from sqlalchemy import select

from app.models import User, UserRole
from tests.conftest import PASSWORD, auth_header

LOGIN = "/api/v1/auth/login"
SETUP = "/api/v1/auth/mfa/setup"
ENABLE = "/api/v1/auth/mfa/enable"
VERIFY = "/api/v1/auth/mfa/verify"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def enroll(client, user) -> tuple[pyotp.TOTP, str]:
    """Parcours complet de la première connexion : mot de passe → configuration → premier code.
    Renvoie le générateur TOTP et le code utilisé pour l'activation."""
    limited = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    setup = client.post(SETUP, headers=bearer(limited["access_token"])).json()
    totp = pyotp.TOTP(setup["secret"])
    code = totp.now()
    response = client.post(ENABLE, headers=bearer(limited["access_token"]), json={"code": code})
    assert response.status_code == 200, response.text
    return totp, code


@pytest.mark.parametrize("role", [UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN])
def test_staff_without_mfa_gets_limited_session(client, make_user, role):
    user = make_user(role)
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    body = response.json()

    assert body["mfa_setup_required"] is True
    assert "set-cookie" not in response.headers  # aucune session longue avant la MFA
    denied = client.get("/test/staff", headers=bearer(body["access_token"]))
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "mfa_required"


def test_staff_token_without_mfa_flag_is_refused_everywhere(client, make_user):
    admin = make_user(UserRole.ADMIN)
    for path in ("/api/v1/auth/me", "/test/any", "/test/admin"):
        assert client.get(path, headers=auth_header(admin, mfa=False)).status_code == 403


def test_enrollment_then_access(client, db, make_user):
    user = make_user(UserRole.CLERK)
    enroll(client, user)
    db.refresh(user)
    assert user.mfa_enabled is True

    access = client.post("/api/v1/auth/refresh").json()["access_token"]  # session complète
    assert client.get("/test/staff", headers=bearer(access)).status_code == 200


def test_mfa_secret_is_encrypted_in_database(client, db, make_user):
    user = make_user(UserRole.MANAGER)
    totp, _ = enroll(client, user)
    stored = db.scalars(select(User.mfa_secret_encrypted).where(User.id == user.id)).one()
    assert stored and totp.secret not in stored


def test_login_with_mfa_requires_code(client, make_user):
    user = make_user(UserRole.ADMIN)
    totp, _ = enroll(client, user)
    client.cookies.clear()

    challenge = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    assert challenge["mfa_required"] is True
    assert "access_token" not in challenge

    # Le jeton de défi n'est pas un jeton d'accès.
    assert client.get("/api/v1/auth/me", headers=bearer(challenge["mfa_token"])).status_code == 401

    wrong = client.post(VERIFY, json={"mfa_token": challenge["mfa_token"], "code": "000000"})
    assert wrong.status_code == 401

    # Code du pas suivant (le code courant a déjà servi à l'activation).
    next_code = totp.at(datetime.now(UTC) + timedelta(seconds=30))
    ok = client.post(VERIFY, json={"mfa_token": challenge["mfa_token"], "code": next_code})
    assert ok.status_code == 200
    assert client.get("/test/admin", headers=bearer(ok.json()["access_token"])).status_code == 200
    assert "ql_refresh" in client.cookies


def test_totp_code_cannot_be_replayed(client, make_user):
    user = make_user(UserRole.CLERK)
    _, used_code = enroll(client, user)  # code déjà utilisé pour l'activation

    challenge = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    replay = client.post(VERIFY, json={"mfa_token": challenge["mfa_token"], "code": used_code})
    assert replay.status_code == 401


def test_cannot_enable_with_wrong_code(client, make_user):
    user = make_user(UserRole.CLERK)
    limited = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    client.post(SETUP, headers=bearer(limited["access_token"]))
    response = client.post(ENABLE, headers=bearer(limited["access_token"]), json={"code": "123456"})
    assert response.status_code == 401


def test_wrong_mfa_codes_count_toward_lockout(client, make_user):
    user = make_user(UserRole.CLERK)
    enroll(client, user)
    challenge = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    for _ in range(5):
        client.post(VERIFY, json={"mfa_token": challenge["mfa_token"], "code": "000000"})
    blocked = client.post(VERIFY, json={"mfa_token": challenge["mfa_token"], "code": "000000"})
    assert blocked.status_code == 423


def test_client_is_not_forced_to_use_mfa(client, make_user):
    user = make_user(UserRole.CLIENT)
    body = client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).json()
    assert body["mfa_setup_required"] is False
    assert client.get("/test/any", headers=bearer(body["access_token"])).status_code == 200
