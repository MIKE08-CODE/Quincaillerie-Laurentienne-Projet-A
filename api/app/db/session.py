"""Connexion à PostgreSQL et session par requête."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,  # vérifie qu'une connexion est encore vivante avant de la réutiliser
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête, toujours refermée à la fin."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
