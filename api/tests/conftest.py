"""Configuration commune des tests.

Les tests utilisent une VRAIE base PostgreSQL (pas SQLite) pour tester le comportement réel :
index sur lower(email), verrous FOR UPDATE, contraintes CHECK. Lancer la base de test :

    docker run -d --name ql-test-db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=quincaillerie_test -p 127.0.0.1:5433:5432 postgres:16-alpine
"""

import os
import secrets

from cryptography.fernet import Fernet

# Variables définies AVANT d'importer l'application, qui lit sa configuration au démarrage.
# Les clés sont générées à chaque exécution : aucun secret, même factice, n'est écrit dans le dépôt.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://test:test@localhost:5433/quincaillerie_test"
)
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["MFA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["RATE_LIMIT_ENABLED"] = "true"

import uuid  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import APIRouter, Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api import deps  # noqa: E402
from app.core import security  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import StaffAssignment, Store, User, UserRole  # noqa: E402
from app.services import email_service  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]
PASSWORD = "Rivière-Pelle-Écrou-42"  # mot de passe valide pour les tests

# Routes réservées aux tests : une par dépendance de deps.py. Elles prouvent le contrôle d'accès
# (A-AUTH-05) avant que les modules commandes et stocks existent; ceux-ci réutiliseront ces dépendances.
_test_router = APIRouter(prefix="/test")


@_test_router.get("/any")
def _any(user: User = Depends(deps.get_current_user)) -> dict:
    return {"ok": True}


@_test_router.get("/staff")
def _staff(
    user: User = Depends(deps.require_roles(UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN)),
) -> dict:
    return {"ok": True}


@_test_router.get("/manager")
def _manager(user: User = Depends(deps.require_roles(UserRole.MANAGER, UserRole.ADMIN))) -> dict:
    return {"ok": True}


@_test_router.get("/admin")
def _admin(user: User = Depends(deps.require_roles(UserRole.ADMIN))) -> dict:
    return {"ok": True}


@_test_router.get("/stores/{store_id}")
def _store(user: User = Depends(deps.require_store_access)) -> dict:
    return {"ok": True}


@_test_router.get("/orders")
def _orders(user: User = Depends(deps.require_verified_email)) -> dict:
    return {"ok": True}


app.include_router(_test_router)


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    """Repart d'une base vide et applique les VRAIES migrations Alembic (on les teste aussi)."""
    config = Config(str(API_DIR / "alembic.ini"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_state() -> Iterator[None]:
    """Chaque test démarre avec des tables vides, une boîte de courriel vide et des compteurs à zéro."""
    email_service.outbox.clear()
    limiter.reset()
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def client() -> TestClient:
    # https : sinon le client de test n'enverrait pas le cookie « Secure ».
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def make_store(db: Session):
    def _make(name: str = "Magasin Laval") -> Store:
        store = Store(name=name, address="1 rue Principale", phone="450-555-0100")
        db.add(store)
        db.commit()
        return store

    return _make


@pytest.fixture
def make_user(db: Session):
    """Crée un utilisateur directement en base (comme le ferait un administrateur)."""

    def _make(
        role: UserRole = UserRole.CLIENT,
        *,
        email: str | None = None,
        password: str = PASSWORD,
        verified: bool = True,
        stores: list[Store] | None = None,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=security.hash_password(password),
            role=role,
            first_name="Test",
            last_name="Utilisateur",
            language="fr",
            email_verified_at=datetime.now(UTC) if verified else None,
            is_active=is_active,
        )
        db.add(user)
        db.flush()
        for store in stores or []:
            db.add(StaffAssignment(user_id=user.id, store_id=store.id))
        db.commit()
        db.refresh(user)
        return user

    return _make


def auth_header(user: User, *, mfa: bool = True) -> dict[str, str]:
    """En-tête d'un jeton d'accès valide, sans passer par /login (utile pour les tests de rôles)."""
    return {"Authorization": f"Bearer {security.create_access_token(user.id, mfa=mfa)}"}


def last_email_token() -> str:
    """Extrait le jeton du dernier courriel envoyé (lien « ...#token=XYZ »)."""
    body = email_service.outbox[-1].body
    return body.split("#token=")[1].split()[0]
