"""A-PRV-01 — Modifier son profil : nom, langue et préférence de communication.

CA : le nom, la langue et les préférences de communication peuvent être enregistrés et relus.
Le courriel, le rôle et le mot de passe ne sont pas modifiables par cette route.
"""

import pytest
from sqlalchemy import select

from app.models import Consent, ConsentType, UserRole
from tests.conftest import auth_header, error_code

ME = "/api/v1/auth/me"


def marketing_rows(db, user) -> list[Consent]:
    db.expire_all()
    return list(
        db.scalars(
            select(Consent)
            .where(Consent.user_id == user.id, Consent.type == ConsentType.MARKETING)
            .order_by(Consent.granted_at)
        )
    )


def test_update_names_and_language_then_read_back(client, make_user):
    user = make_user()
    headers = auth_header(user)

    response = client.patch(
        ME, headers=headers, json={"first_name": "  Marie ", "last_name": "Gagnon", "language": "en"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["first_name"], body["last_name"], body["language"]) == ("Marie", "Gagnon", "en")

    again = client.get(ME, headers=headers).json()  # relu : la modification est enregistrée
    assert (again["first_name"], again["last_name"], again["language"]) == ("Marie", "Gagnon", "en")


def test_partial_update_changes_only_sent_fields(client, make_user):
    user = make_user()
    response = client.patch(ME, headers=auth_header(user), json={"language": "en"})
    assert response.status_code == 200
    assert response.json()["language"] == "en"
    assert response.json()["first_name"] == "Test"  # inchangé
    assert response.json()["last_name"] == "Utilisateur"


def test_empty_body_changes_nothing(client, make_user):
    user = make_user()
    response = client.patch(ME, headers=auth_header(user), json={})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Test"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "pirate@example.com"},
        {"role": "admin"},
        {"password": "Nouveau-Mot-De-Passe-77"},
        {"is_email_verified": True},
        {"first_name": None},
        {"language": None},
        {"marketing_opt_in": None},
        {"first_name": ""},
        {"first_name": "   "},
        {"first_name": "x" * 101},
        {"language": "es"},
    ],
)
def test_invalid_or_forbidden_fields_are_rejected(client, db, make_user, payload):
    user = make_user()
    response = client.patch(ME, headers=auth_header(user), json=payload)
    assert response.status_code == 422
    assert error_code(response) == "validation_error"

    db.refresh(user)
    assert user.role == UserRole.CLIENT  # rien n'a changé
    assert user.email.endswith("@example.com") and not user.email.startswith("pirate")


def test_marketing_opt_in_then_opt_out_keeps_history(client, db, make_user):
    user = make_user()
    headers = auth_header(user)
    assert client.get(ME, headers=headers).json()["marketing_opt_in"] is False

    on = client.patch(ME, headers=headers, json={"marketing_opt_in": True})
    assert on.json()["marketing_opt_in"] is True
    rows = marketing_rows(db, user)
    assert len(rows) == 1 and rows[0].revoked_at is None and rows[0].version

    off = client.patch(ME, headers=headers, json={"marketing_opt_in": False})
    assert off.json()["marketing_opt_in"] is False
    rows = marketing_rows(db, user)
    assert len(rows) == 1 and rows[0].revoked_at is not None  # retiré, mais conservé comme preuve

    client.patch(ME, headers=headers, json={"marketing_opt_in": True})
    rows = marketing_rows(db, user)
    assert len(rows) == 2 and rows[-1].revoked_at is None  # nouvelle preuve datée
    assert client.get(ME, headers=headers).json()["marketing_opt_in"] is True


def test_opt_in_twice_does_not_duplicate_consent(client, db, make_user):
    user = make_user()
    headers = auth_header(user)
    client.patch(ME, headers=headers, json={"marketing_opt_in": True})
    client.patch(ME, headers=headers, json={"marketing_opt_in": True})
    assert len(marketing_rows(db, user)) == 1


def test_opt_out_without_consent_is_harmless(client, db, make_user):
    user = make_user()
    response = client.patch(ME, headers=auth_header(user), json={"marketing_opt_in": False})
    assert response.status_code == 200
    assert marketing_rows(db, user) == []


def test_privacy_consent_is_never_touched(client, db, make_user):
    """Retirer le marketing ne touche pas au consentement obligatoire à la politique de confidentialité."""
    user = make_user()
    db.add(Consent(user_id=user.id, type=ConsentType.PRIVACY, version="1.0"))
    db.commit()

    client.patch(ME, headers=auth_header(user), json={"marketing_opt_in": False})
    db.expire_all()
    privacy = db.scalars(
        select(Consent).where(Consent.user_id == user.id, Consent.type == ConsentType.PRIVACY)
    ).one()
    assert privacy.revoked_at is None


def test_marketing_chosen_at_registration_is_visible(client, db):
    """Le choix fait à l'inscription (A-AUTH-01) est relu par GET /auth/me."""
    from app.models import User
    from tests.conftest import PASSWORD

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "marie.inscription@example.com",
            "password": PASSWORD,
            "first_name": "Marie",
            "last_name": "Gagnon",
            "accept_privacy_policy": True,
            "marketing_opt_in": True,
        },
    )
    user = db.scalars(select(User).where(User.email == "marie.inscription@example.com")).one()
    assert client.get(ME, headers=auth_header(user)).json()["marketing_opt_in"] is True


def test_profile_requires_authentication(client):
    assert client.patch(ME, json={"language": "en"}).status_code == 401


def test_staff_without_mfa_cannot_update_profile(client, make_user):
    clerk = make_user(UserRole.CLERK)
    response = client.patch(ME, headers=auth_header(clerk, mfa=False), json={"language": "en"})
    assert response.status_code == 403
    assert error_code(response) == "mfa_required"


def test_staff_with_mfa_can_update_own_name(client, make_user):
    clerk = make_user(UserRole.CLERK)
    response = client.patch(ME, headers=auth_header(clerk), json={"first_name": "Luc"})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Luc"
    assert response.json()["role"] == "clerk"
