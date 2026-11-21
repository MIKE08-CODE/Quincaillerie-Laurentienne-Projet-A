"""A-AUTH-03 — CA : mots de passe faibles refusés avec un message clair;
aucun mot de passe en clair dans la BD ou les journaux."""

import logging

import pytest
from sqlalchemy import select

from app.core.errors import ValidationFailed
from app.models import User
from app.services.password_policy import validate_password
from tests.conftest import PASSWORD


@pytest.mark.parametrize(
    ("password", "code"),
    [
        ("Court-1", "password_too_short"),
        ("a" * 129, "password_too_long"),
        ("password1234", "password_too_common"),
        ("PASSWORD1234", "password_too_common"),  # insensible à la casse
        ("123456789012", "password_too_common"),
        ("abababababab", "password_too_simple"),
        ("Quincaillerie-2026", "password_contains_personal_info"),
        ("jean.tremblay-2026!", "password_contains_personal_info"),
    ],
)
def test_weak_passwords_are_refused(password, code):
    with pytest.raises(ValidationFailed) as error:
        validate_password(
            password, email="jean.tremblay@example.com", first_name="Jean", last_name="Tremblay"
        )
    assert error.value.code == code
    assert error.value.message  # message clair à afficher


def test_strong_password_is_accepted():
    validate_password(PASSWORD, email="jean@example.com", first_name="Jean", last_name="Tremblay")


def test_weak_password_gives_clear_api_error(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "faible@example.com",
            "password": "password1234",
            "first_name": "Ana",
            "last_name": "Roy",
            "accept_privacy_policy": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "password_too_common"


def test_password_never_stored_or_logged_in_clear(client, db, caplog):
    caplog.set_level(logging.DEBUG)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "clair@example.com",
            "password": PASSWORD,
            "first_name": "Ana",
            "last_name": "Roy",
            "accept_privacy_policy": True,
        },
    )
    client.post("/api/v1/auth/login", json={"email": "clair@example.com", "password": PASSWORD})

    user = db.scalars(select(User).where(User.email == "clair@example.com")).one()
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash
    assert PASSWORD not in caplog.text
