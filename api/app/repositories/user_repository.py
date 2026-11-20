"""Accès aux données des utilisateurs et des consentements. Aucune règle métier ici."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Consent, User


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str, *, for_update: bool = False) -> User | None:
    """Recherche insensible à la casse. `for_update` verrouille la ligne jusqu'à la fin de la
    transaction : deux connexions simultanées ne peuvent pas fausser le compteur d'échecs."""
    stmt = select(User).where(func.lower(User.email) == email.lower())
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalars(stmt).first()


def lock_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.scalars(select(User).where(User.id == user_id).with_for_update()).first()


def add(db: Session, user: User) -> User:
    db.add(user)
    db.flush()  # obtient l'id sans valider la transaction (le service décide du commit)
    return user


def add_consent(db: Session, consent: Consent) -> Consent:
    db.add(consent)
    db.flush()
    return consent
