"""Comptes de démonstration par rôle (cahier §6.3) : création, sécurité des mots de passe, idempotence."""

import secrets

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.errors import ValidationFailed
from app.models import StaffAssignment, User, UserRole
from app.seed import demo_accounts, seed_l1


@pytest.fixture
def store_ready(db: Session):
    seed_l1._seed_stores(db, seed_l1.SeedReport())  # seuls les magasins sont nécessaires
    db.commit()


@pytest.fixture
def passwords(monkeypatch) -> dict[str, str]:
    """Mots de passe générés à l'exécution (jamais de valeur littérale dans le dépôt)."""
    values = {a.key: f"{secrets.token_urlsafe(18)}-{i}" for i, a in enumerate(demo_accounts.ACCOUNTS)}
    for account in demo_accounts.ACCOUNTS:
        monkeypatch.setenv(account.env_var, values[account.key])
    return values


def _users(db: Session) -> dict[str, User]:
    return {u.email: u for u in db.scalars(select(User))}


def test_creates_one_verified_account_per_role(db: Session, store_ready, passwords):
    results = demo_accounts.run(db, domain="example.com")
    users = _users(db)
    assert {r.role for r in results} == {"client", "clerk", "manager", "admin"}
    assert {users[r.email].role for r in results} == set(UserRole)
    for account in demo_accounts.ACCOUNTS:
        user = users[demo_accounts.email_for(account, "example.com")]
        assert user.password_hash.startswith("$argon2id$")  # jamais en clair
        assert passwords[account.key] not in user.password_hash
        assert security.verify_password(passwords[account.key], user.password_hash)
        assert user.email_verified_at is not None and user.is_active
    assert all(r.status == "créé" for r in results)


def test_results_never_carry_passwords(db: Session, store_ready, passwords):
    results = demo_accounts.run(db, domain="example.com")
    dumped = repr(results)
    assert not any(p in dumped for p in passwords.values())


def test_staff_are_assigned_to_the_demo_store(db: Session, store_ready, passwords):
    demo_accounts.run(db, domain="example.com")
    users = _users(db)
    assigned = {a.user_id for a in db.scalars(select(StaffAssignment))}
    assert users["demo-commis@example.com"].id in assigned
    assert users["demo-gerant@example.com"].id in assigned
    assert users["demo-client@example.com"].id not in assigned
    assert users["demo-admin@example.com"].id not in assigned


def test_is_idempotent_and_never_changes_existing_passwords(db: Session, store_ready, passwords, monkeypatch):
    demo_accounts.run(db, domain="example.com")
    hashes = {e: u.password_hash for e, u in _users(db).items()}
    for account in demo_accounts.ACCOUNTS:  # même sans variables, un compte existant est laissé tel quel
        monkeypatch.delenv(account.env_var)
    second = demo_accounts.run(db, domain="example.com")
    assert {r.status for r in second} == {"existant"}
    db.expire_all()
    assert {e: u.password_hash for e, u in _users(db).items()} == hashes


def test_reset_replaces_password_and_invalidates_sessions(db: Session, store_ready, passwords, monkeypatch):
    demo_accounts.run(db, domain="example.com")
    new_admin_password = f"{secrets.token_urlsafe(18)}-n"
    monkeypatch.setenv("DEMO_PASSWORD_ADMIN", new_admin_password)
    results = demo_accounts.run(db, domain="example.com", reset=True)
    db.expire_all()
    admin = db.scalar(select(User).where(User.email == "demo-admin@example.com"))
    assert security.verify_password(new_admin_password, admin.password_hash)
    assert admin.tokens_valid_after is not None
    assert {r.status for r in results} == {"réinitialisé"}


def test_weak_password_is_refused_and_nothing_is_created(db: Session, store_ready, passwords, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD_ADMIN", "motdepasse")
    with pytest.raises(ValidationFailed):
        demo_accounts.run(db, domain="example.com")
    db.rollback()
    assert _users(db) == {}  # tout ou rien


def test_password_containing_the_account_name_is_refused(db: Session, store_ready, passwords, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD_CLIENT", f"client-{secrets.token_urlsafe(12)}")
    with pytest.raises(ValidationFailed) as excinfo:
        demo_accounts.run(db, domain="example.com")
    assert excinfo.value.code == "password_contains_personal_info"


def test_missing_password_is_refused(db: Session, store_ready, passwords, monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD_GERANT")
    with pytest.raises(ValidationFailed) as excinfo:
        demo_accounts.run(db, domain="example.com")
    assert excinfo.value.code == "demo_password_missing"


def test_requires_the_seeded_store(db: Session, passwords):
    with pytest.raises(ValidationFailed) as excinfo:
        demo_accounts.run(db, domain="example.com")
    assert excinfo.value.code == "demo_store_missing"


def test_demo_staff_must_set_up_mfa_before_admin_routes(client, db: Session, store_ready, passwords):
    demo_accounts.run(db, domain="example.com")
    login = client.post(
        "/api/v1/auth/login", json={"email": "demo-admin@example.com", "password": passwords["admin"]}
    )
    assert login.status_code == 200 and login.json()["mfa_setup_required"] is True
    token = login.json()["access_token"]
    blocked = client.get("/api/v1/admin/products", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 403  # MFA obligatoire avant toute route d'administration


def test_demo_client_can_log_in(client, db: Session, store_ready, passwords):
    demo_accounts.run(db, domain="example.com")
    login = client.post(
        "/api/v1/auth/login", json={"email": "demo-client@example.com", "password": passwords["client"]}
    )
    assert login.status_code == 200 and login.json()["access_token"]


def test_production_requires_explicit_flag(monkeypatch, capsys):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert demo_accounts.main([]) == 2
    assert "Refusé" in capsys.readouterr().err


def test_command_output_never_contains_passwords(db: Session, store_ready, passwords, capsys, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: db)
    assert demo_accounts.main([]) == 0
    captured = capsys.readouterr()
    assert "demo-admin@example.com" in captured.out
    assert not any(p in captured.out + captured.err for p in passwords.values())
