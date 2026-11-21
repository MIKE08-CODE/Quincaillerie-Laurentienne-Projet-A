"""A-AUTH-01 — Inscription, consentement, vérification du courriel.
CA : un compte non vérifié ne peut pas passer de commande; l'horodatage du consentement est enregistré."""

from sqlalchemy import func, select

from app.models import Consent, ConsentType, User, UserRole
from app.services import email_service
from tests.conftest import PASSWORD, auth_header, last_email_token

URL = "/api/v1/auth/register"


def payload(**overrides):
    data = {
        "email": "Marie.Gagnon@Example.com",
        "password": PASSWORD,
        "first_name": "Marie",
        "last_name": "Gagnon",
        "language": "fr",
        "accept_privacy_policy": True,
    }
    return {**data, **overrides}


def test_register_creates_unverified_client_with_timestamped_consent(client, db):
    response = client.post(URL, json=payload())
    assert response.status_code == 202

    user = db.scalars(select(User)).one()
    assert user.email == "marie.gagnon@example.com"  # normalisé en minuscules
    assert user.role == UserRole.CLIENT
    assert user.email_verified_at is None

    consent = db.scalars(select(Consent).where(Consent.user_id == user.id)).one()
    assert consent.type == ConsentType.PRIVACY
    assert consent.version
    assert consent.granted_at is not None  # horodatage du consentement

    assert email_service.outbox[-1].to == "marie.gagnon@example.com"
    assert "#token=" in email_service.outbox[-1].body


def test_marketing_consent_only_when_opted_in(client, db):
    client.post(URL, json=payload(marketing_opt_in=True))
    types = set(db.scalars(select(Consent.type)))
    assert types == {ConsentType.PRIVACY, ConsentType.MARKETING}


def test_privacy_consent_is_mandatory(client):
    assert client.post(URL, json=payload(accept_privacy_policy=False)).status_code == 422
    body = payload()
    del body["accept_privacy_policy"]
    assert client.post(URL, json=body).status_code == 422


def test_cannot_choose_own_role(client, db):
    """Un champ « role » est refusé : personne ne peut s'inscrire administrateur."""
    assert client.post(URL, json=payload(role="admin")).status_code == 422
    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_duplicate_email_same_response_and_owner_notified(client, db):
    first = client.post(URL, json=payload())
    second = client.post(URL, json=payload(email="MARIE.GAGNON@example.com"))  # autre casse

    assert second.status_code == first.status_code == 202
    assert second.json() == first.json()  # aucune énumération
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert email_service.outbox[-1].subject == "Tentative d'inscription"


def test_email_verification_flow_and_single_use(client, db):
    client.post(URL, json=payload())
    token = last_email_token()

    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    user = db.scalars(select(User)).one()
    db.refresh(user)
    assert user.email_verified_at is not None

    reused = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert reused.status_code == 400
    assert reused.json()["detail"]["code"] == "invalid_or_expired_token"


def test_resend_verification_invalidates_previous_link(client):
    client.post(URL, json=payload())
    old_token = last_email_token()
    response = client.post("/api/v1/auth/verify-email/resend", json={"email": "marie.gagnon@example.com"})
    assert response.status_code == 202
    new_token = last_email_token()

    assert client.post("/api/v1/auth/verify-email", json={"token": old_token}).status_code == 400
    assert client.post("/api/v1/auth/verify-email", json={"token": new_token}).status_code == 200


def test_resend_same_response_for_unknown_email(client):
    known = client.post("/api/v1/auth/verify-email/resend", json={"email": "inconnu@example.com"})
    assert known.status_code == 202
    assert email_service.outbox == []


def test_unverified_account_cannot_order(client, make_user):
    """La dépendance require_verified_email sera posée sur le paiement (module commandes)."""
    unverified = make_user(verified=False)
    verified = make_user()
    assert client.get("/test/orders", headers=auth_header(unverified)).json()["detail"]["code"] == (
        "email_not_verified"
    )
    assert client.get("/test/orders", headers=auth_header(verified)).status_code == 200
