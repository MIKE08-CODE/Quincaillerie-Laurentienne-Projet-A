"""Comptes de démonstration par rôle (cahier §6.3) : création, sécurité des mots de passe, idempotence."""

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


def _users(db: Session) -> dict[str, User]:
    return {u.email: u for u in db.scalars(select(User))}


def test_creates_one_account_per_role_with_generated_passwords(db: Session, store_ready):
    results = demo_accounts.run(db, domain="example.com", generate=True)
    users = _users(db)
    assert {r.role for r in results} == {"client", "clerk", "manager", "admin"}
    assert {users[r.email].role for r in results} == set(UserRole)
    for r in results:
        user = users[r.email]
        assert r.status == "créé" and r.generated_password and len(r.generated_password) >= 20
        assert user.password_hash.startswith("$argon2id$")  # jamais en clair
        assert r.generated_password not in user.password_hash
        assert security.verify_password(r.generated_password, user.password_hash)
        assert user.email_verified_at is not None and user.is_active
    # Mots de passe tous différents
    assert len({r.generated_password for r in results}) == 4


def test_staff_are_assigned_to_the_demo_store(db: Session, store_ready):
    demo_accounts.run(db, domain="example.com", generate=True)
    users = _users(db)
    assigned = {a.user_id for a in db.scalars(select(StaffAssignment))}
    assert users["demo-commis@example.com"].id in assigned
    assert users["demo-gerant@example.com"].id in assigned
    assert users["demo-client@example.com"].id not in assigned


def test_is_idempotent_and_never_changes_existing_passwords(db: Session, store_ready):
    first = demo_accounts.run(db, domain="example.com", generate=True)
    hashes = {e: u.password_hash for e, u in _users(db).items()}
    second = demo_accounts.run(db, domain="example.com", generate=True)
    assert all(r.status == "existant" and r.generated_password is None for r in second)
    db.expire_all()
    assert {e: u.password_hash for e, u in _users(db).items()} == hashes
    assert len(_users(db)) == len(first)


def test_reset_replaces_password_and_invalidates_sessions(db: Session, store_ready):
    demo_accounts.run(db, domain="example.com", generate=True)
    [admin_before] = [u for u in _users(db).values() if u.role == UserRole.ADMIN]
    old_hash = admin_before.password_hash
    results = demo_accounts.run(db, domain="example.com", generate=True, reset=True)
    db.expire_all()
    admin = db.scalar(select(User).where(User.email == "demo-admin@example.com"))
    assert admin.password_hash != old_hash and admin.tokens_valid_after is not None
    assert {r.status for r in results} == {"réinitialisé"}


def test_passwords_from_environment_are_used_and_not_returned(db: Session, store_ready, monkeypatch):
    # Les mots de passe ne doivent pas contenir le nom du compte (politique A-AUTH-03).
    for i, key in enumerate(("CLIENT", "COMMIS", "GERANT", "ADMIN")):
        monkeypatch.setenv(f"DEMO_PASSWORD_{key}", f"Marteau-Vis-Equerre-{i}-2026")
    results = demo_accounts.run(db, domain="demo.example.org", generate=False)
    assert all(r.generated_password is None for r in results)
    admin = db.scalar(select(User).where(User.email == "demo-admin@demo.example.org"))
    assert security.verify_password("Marteau-Vis-Equerre-3-2026", admin.password_hash)


def test_weak_password_from_environment_is_refused(db: Session, store_ready, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD_CLIENT", "motdepasse")
    with pytest.raises(ValidationFailed):
        demo_accounts.run(db, domain="example.com", generate=True)
    db.rollback()
    assert _users(db) == {}  # tout ou rien


def test_missing_password_without_generation_is_refused(db: Session, store_ready, monkeypatch):
    for key in ("CLIENT", "COMMIS", "GERANT", "ADMIN"):
        monkeypatch.delenv(f"DEMO_PASSWORD_{key}", raising=False)
    with pytest.raises(ValidationFailed) as excinfo:
        demo_accounts.run(db, domain="example.com", generate=False)
    assert excinfo.value.code == "demo_password_missing"


def test_requires_the_seeded_store(db: Session):
    with pytest.raises(ValidationFailed) as excinfo:
        demo_accounts.run(db, domain="example.com", generate=True)
    assert excinfo.value.code == "demo_store_missing"


def test_demo_staff_must_set_up_mfa_and_admin_routes_are_reachable_after(client, db: Session, store_ready):
    results = demo_accounts.run(db, domain="example.com", generate=True)
    admin = next(r for r in results if r.role == "admin")
    login = client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": admin.generated_password}
    )
    assert login.status_code == 200 and login.json()["mfa_setup_required"] is True
    blocked = client.get(
        "/api/v1/admin/products", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert blocked.status_code == 403  # MFA obligatoire avant toute route d'administration


@pytest.mark.parametrize("args", [[], ["--generer", "--allow-production"]])
def test_production_safeguards(monkeypatch, capsys, args):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert demo_accounts.main(args) == 2
    assert "Refusé" in capsys.readouterr().err


def test_generated_passwords_are_printed_once_and_only_on_stdout(
    db: Session, store_ready, capsys, monkeypatch
):
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: db)
    assert demo_accounts.main(["--generer"]) == 0
    out = capsys.readouterr().out
    assert out.count("demo-admin@example.com :") == 1
    assert demo_accounts.main(["--generer"]) == 0
    assert "Mots de passe générés" not in capsys.readouterr().out  # rien de nouveau à afficher
