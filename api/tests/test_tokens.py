"""A-AUTH-02 — Jeton d'accès court + jeton de rafraîchissement en cookie httpOnly, Secure, SameSite.
CA : jeton expiré → 401; le rafraîchissement fonctionne; un jeton révoqué est rejeté."""

from datetime import timedelta

import jwt
from sqlalchemy import select

from app.core import security
from app.core.config import get_settings
from app.models import RefreshToken
from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def login(client, user):
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_short_access_token_and_secure_refresh_cookie(client, make_user):
    user = make_user()
    response = login(client, user)
    body = response.json()

    assert body["token_type"] == "bearer"
    assert body["expires_in"] <= 15 * 60
    assert "refresh_token" not in body  # jamais dans le corps : seulement dans le cookie

    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] <= 15 * 60

    cookie = response.headers["set-cookie"].lower()
    assert "ql_refresh=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie

    me = client.get(ME, headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == user.email
    assert "password_hash" not in me.json()


def test_wrong_password_and_unknown_email_give_same_error(client, make_user):
    user = make_user()
    wrong = client.post(LOGIN, json={"email": user.email, "password": "Mauvais-mot-de-passe-1"})
    unknown = client.post(LOGIN, json={"email": "personne@example.com", "password": "Mauvais-mot-de-passe-1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_inactive_account_cannot_login(client, make_user):
    user = make_user(is_active=False)
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_expired_access_token_is_401(client, make_user):
    user = make_user()
    expired = security.create_jwt(user.id, "access", timedelta(seconds=-1), mfa=False)
    response = client.get(ME, headers=bearer(expired))
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_tampered_or_wrongly_signed_token_is_401(client, make_user):
    user = make_user()
    forged = jwt.encode({"sub": str(user.id), "type": "access", "iat": 0, "exp": 9999999999}, "autre-cle")
    assert client.get(ME, headers=bearer(forged)).status_code == 401
    none_alg = jwt.encode({"sub": str(user.id), "type": "access", "iat": 0, "exp": 9999999999}, None, "none")
    assert client.get(ME, headers=bearer(none_alg)).status_code == 401


def test_missing_token_is_401(client):
    assert client.get(ME).status_code == 401


def test_refresh_works_and_rotates_token(client, make_user):
    user = make_user()
    login(client, user)
    old_cookie = client.cookies.get("ql_refresh")

    response = client.post(REFRESH)
    assert response.status_code == 200
    assert client.get(ME, headers=bearer(response.json()["access_token"])).status_code == 200
    assert client.cookies.get("ql_refresh") != old_cookie  # nouveau jeton à chaque fois


def test_reused_refresh_token_is_rejected_and_revokes_all_sessions(client, db, make_user):
    """Un jeton déjà échangé qui revient = vol probable : toutes les sessions sont fermées."""
    user = make_user()
    login(client, user)
    stolen = client.cookies.get("ql_refresh")
    assert client.post(REFRESH).status_code == 200  # le vrai propriétaire rafraîchit

    client.cookies.set("ql_refresh", stolen, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # le voleur est rejeté

    active = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    assert active == []  # le propriétaire aussi doit se reconnecter


def test_logout_revokes_refresh_token(client, make_user):
    user = make_user()
    login(client, user)
    token = client.cookies.get("ql_refresh")

    response = client.post(LOGOUT)
    assert response.status_code == 204
    assert (
        'ql_refresh=""' in response.headers["set-cookie"]
        or "max-age=0" in response.headers["set-cookie"].lower()
    )

    client.cookies.set("ql_refresh", token, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # jeton révoqué → rejeté


def test_refresh_without_cookie_is_401(client):
    assert client.post(REFRESH).status_code == 401


def test_expired_refresh_token_is_rejected(client, db, make_user):
    user = make_user()
    login(client, user)
    stored = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)).one()
    stored.expires_at = stored.created_at - timedelta(seconds=1)
    db.commit()
    assert client.post(REFRESH).status_code == 401


def test_refresh_token_stored_only_as_hash(client, db, make_user):
    user = make_user()
    login(client, user)
    raw = client.cookies.get("ql_refresh")
    stored = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)).one()
    assert stored.token_hash != raw
    assert stored.token_hash == security.hash_token(raw)


def test_access_lifetime_setting(client):
    assert get_settings().access_token_expire_minutes <= 15
