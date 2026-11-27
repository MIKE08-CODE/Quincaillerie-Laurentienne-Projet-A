"""DEC-02 — Session des clients natifs (application mobile, application de bureau).

Les applications natives ne gèrent pas les cookies de façon fiable : avec `client: "native"`, le
jeton de rafraîchissement est renvoyé dans le corps JSON et jamais en cookie. Le web n'est pas
touché, et un jeton reçu par cookie n'est JAMAIS recopié dans le JSON (protection contre un XSS).
"""

from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import select

from app.models import RefreshToken, UserRole
from tests.conftest import PASSWORD, last_email_token

NEW_PASSWORD = "Nouveau-Tournevis-Étoile-77"  # noqa: S105 — mot de passe de test  # nosec B105
FORGOT = "/api/v1/auth/password/forgot"
RESET = "/api/v1/auth/password/reset"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
SETUP = "/api/v1/auth/mfa/setup"
ENABLE = "/api/v1/auth/mfa/enable"
VERIFY = "/api/v1/auth/mfa/verify"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def native_login(client, user) -> dict:
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD, "client": "native"})
    assert response.status_code == 200, response.text
    assert "set-cookie" not in response.headers  # aucun cookie pour un client natif
    return response.json()


def test_native_login_returns_refresh_token_in_body_without_cookie(client, make_user):
    user = make_user()
    body = native_login(client, user)

    assert body["refresh_token"]
    assert 0 < body["refresh_expires_in"] <= 7 * 24 * 3600
    assert body["expires_in"] <= 15 * 60
    assert client.cookies.get("ql_refresh") is None
    assert client.get(ME, headers=bearer(body["access_token"])).status_code == 200


def test_web_login_is_unchanged(client, make_user):
    """Sans `client` (ou avec "web") : cookie seulement, aucune clé `refresh_token` dans le JSON."""
    user = make_user()
    for payload in ({}, {"client": "web"}):
        response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD, **payload})
        assert response.status_code == 200
        assert "refresh_token" not in response.json()
        assert "refresh_expires_in" not in response.json()
        assert "ql_refresh=" in response.headers["set-cookie"]


def test_unknown_client_kind_is_rejected(client, make_user):
    user = make_user()
    response = client.post(LOGIN, json={"email": user.email, "password": PASSWORD, "client": "ios"})
    assert response.status_code == 422


def test_native_refresh_rotates_token_in_body(client, make_user):
    user = make_user()
    first = native_login(client, user)["refresh_token"]

    response = client.post(REFRESH, json={"refresh_token": first})
    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    second = response.json()["refresh_token"]
    assert second and second != first
    assert client.get(ME, headers=bearer(response.json()["access_token"])).status_code == 200

    # L'ancien jeton est inutilisable après la rotation.
    assert client.post(REFRESH, json={"refresh_token": first}).status_code == 401


def test_reused_native_token_revokes_all_sessions(client, db, make_user):
    """Un jeton déjà échangé qui revient = vol probable : toutes les sessions sont fermées."""
    user = make_user()
    stolen = native_login(client, user)["refresh_token"]
    current = client.post(REFRESH, json={"refresh_token": stolen}).json()["refresh_token"]

    assert client.post(REFRESH, json={"refresh_token": stolen}).status_code == 401
    assert client.post(REFRESH, json={"refresh_token": current}).status_code == 401
    active = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    assert active == []


def test_cookie_refresh_never_returns_token_in_body(client, make_user):
    """Protection XSS : un jeton reçu par cookie ne doit jamais être lisible dans la réponse."""
    user = make_user()
    client.post(LOGIN, json={"email": user.email, "password": PASSWORD})

    response = client.post(REFRESH)  # aucun corps : mode web
    assert response.status_code == 200
    assert "refresh_token" not in response.json()
    assert "ql_refresh=" in response.headers["set-cookie"]


def test_native_logout_revokes_token(client, make_user):
    user = make_user()
    token = native_login(client, user)["refresh_token"]

    response = client.post(LOGOUT, json={"refresh_token": token})
    assert response.status_code == 204
    assert "set-cookie" not in response.headers  # rien à effacer côté natif
    assert client.post(REFRESH, json={"refresh_token": token}).status_code == 401


def test_native_logout_with_unknown_token_still_succeeds(client):
    """Comme pour le web : 204 sans révéler si le jeton existait."""
    assert client.post(LOGOUT, json={"refresh_token": "inconnu"}).status_code == 204


def test_invalid_native_bodies_are_rejected(client):
    for body in (
        {"refresh_token": ""},
        {"refresh_token": "x" * 300},
        {"refresh_token": "a", "role": "admin"},
    ):
        assert client.post(REFRESH, json=body).status_code == 422
        assert client.post(LOGOUT, json=body).status_code == 422


def test_unknown_native_refresh_token_is_401(client):
    assert client.post(REFRESH, json={"refresh_token": "inconnu"}).status_code == 401


def test_password_reset_revokes_native_sessions(client, make_user):
    """Une réinitialisation du mot de passe ferme aussi les sessions mobiles."""
    user = make_user()
    token = native_login(client, user)["refresh_token"]

    client.post(FORGOT, json={"email": user.email})
    reset = client.post(RESET, json={"token": last_email_token(), "new_password": NEW_PASSWORD})
    assert reset.status_code == 200

    assert client.post(REFRESH, json={"refresh_token": token}).status_code == 401


def test_staff_without_mfa_gets_no_refresh_token_even_in_native_mode(client, make_user):
    clerk = make_user(UserRole.CLERK)
    response = client.post(LOGIN, json={"email": clerk.email, "password": PASSWORD, "client": "native"})
    body = response.json()

    assert body["mfa_setup_required"] is True
    assert "refresh_token" not in body
    assert "set-cookie" not in response.headers


def test_staff_native_mfa_enable_and_verify(client, make_user):
    """Personnel sur l'application de bureau : activation puis connexion MFA en mode natif."""
    clerk = make_user(UserRole.CLERK)
    limited = client.post(
        LOGIN, json={"email": clerk.email, "password": PASSWORD, "client": "native"}
    ).json()["access_token"]
    secret = client.post(SETUP, headers=bearer(limited)).json()["secret"]
    totp = pyotp.TOTP(secret)

    enabled = client.post(ENABLE, headers=bearer(limited), json={"code": totp.now(), "client": "native"})
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["refresh_token"]
    assert "set-cookie" not in enabled.headers

    challenge = client.post(
        LOGIN, json={"email": clerk.email, "password": PASSWORD, "client": "native"}
    ).json()
    assert challenge["mfa_required"] is True

    # Le code de l'activation ne peut pas être rejoué : on prend celui du pas de temps suivant.
    code = totp.at(datetime.now(UTC) + timedelta(seconds=30))
    verified = client.post(
        VERIFY, json={"mfa_token": challenge["mfa_token"], "code": code, "client": "native"}
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["refresh_token"]
    assert "set-cookie" not in verified.headers
