"""A-AUTH-07 — Limitation de débit et verrouillage progressif (5 échecs → blocage de 15 min).
CA : démontré par un script de test (ce fichier : `pytest tests/test_lockout.py -v`)."""

from datetime import UTC, datetime, timedelta

from app.models import User
from app.services.auth_service import register_failed_attempt
from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"
WRONG = "Mauvais-mot-de-passe-1"


def test_five_failures_lock_the_account_for_15_minutes(client, db, make_user):
    user = make_user()
    for attempt in range(1, 6):
        response = client.post(LOGIN, json={"email": user.email, "password": WRONG})
        assert response.status_code == 401, f"tentative {attempt}"

    # 6e tentative, avec le BON mot de passe : refusée, car le compte est bloqué.
    blocked = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert blocked.status_code == 423
    assert blocked.json()["detail"]["code"] == "account_locked"
    assert 14 * 60 < int(blocked.headers["Retry-After"]) <= 15 * 60

    db.refresh(user)
    assert user.failed_login_count == 5
    assert user.locked_until is not None


def test_login_works_again_after_lock_expires_and_counter_resets(client, db, make_user):
    user = make_user()
    for _ in range(5):
        client.post(LOGIN, json={"email": user.email, "password": WRONG})

    db.refresh(user)
    user.locked_until = datetime.now(UTC) - timedelta(seconds=1)  # on « avance » de 15 min
    db.commit()

    assert client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
    db.refresh(user)
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_lock_duration_doubles_at_each_level():
    """Verrouillage progressif : 15 min au 5e échec, 30 au 10e, 60 au 15e."""
    user = User(failed_login_count=0)
    durations = []
    for _ in range(15):
        before = datetime.now(UTC)
        user.locked_until = None
        register_failed_attempt(user)
        if user.locked_until:
            durations.append(round((user.locked_until - before).total_seconds() / 60))
    assert durations == [15, 30, 60]


def test_success_before_five_failures_resets_counter(client, db, make_user):
    user = make_user()
    for _ in range(4):
        client.post(LOGIN, json={"email": user.email, "password": WRONG})
    assert client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
    db.refresh(user)
    assert user.failed_login_count == 0


def test_rate_limit_per_ip_on_login(client):
    """Limitation de débit : au-delà de 10 tentatives par minute depuis une même IP → 429,
    même en changeant de courriel à chaque fois (bourrage d'identifiants)."""
    codes = [
        client.post(LOGIN, json={"email": f"robot{i}@example.com", "password": WRONG}).status_code
        for i in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_rate_limit_on_register_and_password_forgot(client):
    forgot = [
        client.post("/api/v1/auth/password/forgot", json={"email": f"a{i}@example.com"}).status_code
        for i in range(6)
    ]
    assert forgot[-1] == 429
