"""A-AUTH-04 — Réinitialisation par jeton à usage unique de 30 min.
CA : la réutilisation du jeton échoue; aucune énumération d'utilisateurs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import OneTimeToken, OneTimeTokenPurpose, RefreshToken
from app.services import email_service
from tests.conftest import PASSWORD, last_email_token

FORGOT = "/api/v1/auth/password/forgot"
RESET = "/api/v1/auth/password/reset"
NEW_PASSWORD = "Nouveau-Tournevis-Étoile-77"


def test_same_response_whether_email_exists_or_not(client, make_user):
    user = make_user()
    existing = client.post(FORGOT, json={"email": user.email})
    unknown = client.post(FORGOT, json={"email": "personne@example.com"})

    assert existing.status_code == unknown.status_code == 202
    assert existing.json() == unknown.json()
    assert len(email_service.outbox) == 1  # seul le vrai compte reçoit un courriel
    assert email_service.outbox[0].to == user.email


def test_reset_token_expires_after_30_minutes(client, db, make_user):
    user = make_user()
    client.post(FORGOT, json={"email": user.email})
    stored = db.scalars(select(OneTimeToken).where(OneTimeToken.user_id == user.id)).one()
    lifetime = stored.expires_at - stored.created_at
    assert timedelta(minutes=29) < lifetime <= timedelta(minutes=30, seconds=5)

    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    response = client.post(RESET, json={"token": last_email_token(), "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_or_expired_token"


def test_reset_changes_password_and_token_cannot_be_reused(client, make_user):
    user = make_user()
    client.post(FORGOT, json={"email": user.email})
    token = last_email_token()

    assert client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD}).status_code == 200
    assert (
        client.post(RESET, json={"token": token, "new_password": "Autre-Marteau-Bleu-99"}).status_code == 400
    )

    login = "/api/v1/auth/login"
    assert client.post(login, json={"email": user.email, "password": PASSWORD}).status_code == 401
    assert client.post(login, json={"email": user.email, "password": NEW_PASSWORD}).status_code == 200


def test_reset_closes_all_existing_sessions(client, db, make_user):
    user = make_user()
    client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    client.post(FORGOT, json={"email": user.email})
    client.post(RESET, json={"token": last_email_token(), "new_password": NEW_PASSWORD})

    active = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    assert active == []


def test_weak_new_password_is_refused_and_token_stays_usable(client, make_user):
    user = make_user()
    client.post(FORGOT, json={"email": user.email})
    token = last_email_token()

    weak = client.post(RESET, json={"token": token, "new_password": "password1234"})
    assert weak.status_code == 422
    assert weak.json()["detail"]["code"] == "password_too_common"
    assert client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD}).status_code == 200


def test_new_request_invalidates_previous_link(client, make_user):
    user = make_user()
    client.post(FORGOT, json={"email": user.email})
    first = last_email_token()
    client.post(FORGOT, json={"email": user.email})
    second = last_email_token()

    assert client.post(RESET, json={"token": first, "new_password": NEW_PASSWORD}).status_code == 400
    assert client.post(RESET, json={"token": second, "new_password": NEW_PASSWORD}).status_code == 200


def test_verification_token_cannot_be_used_as_reset_token(client, db, make_user):
    user = make_user(verified=False)
    client.post("/api/v1/auth/verify-email/resend", json={"email": user.email})
    verification_token = last_email_token()
    response = client.post(RESET, json={"token": verification_token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    purposes = set(db.scalars(select(OneTimeToken.purpose)))
    assert purposes == {OneTimeTokenPurpose.EMAIL_VERIFICATION}
