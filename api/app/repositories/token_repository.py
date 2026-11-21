"""Accès aux jetons de rafraîchissement et aux jetons à usage unique."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OneTimeToken, OneTimeTokenPurpose, RefreshToken


# --- Jetons de rafraîchissement ---
def add_refresh_token(db: Session, token: RefreshToken) -> None:
    db.add(token)
    db.flush()


def get_refresh_token_for_update(db: Session, token_hash: str) -> RefreshToken | None:
    """Verrouille la ligne : deux rafraîchissements simultanés ne peuvent pas tous deux réussir."""
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    return db.scalars(stmt).first()


def revoke_all_refresh_tokens(db: Session, user_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


# --- Jetons à usage unique ---
def add_one_time_token(db: Session, token: OneTimeToken) -> None:
    db.add(token)
    db.flush()


def get_one_time_token_for_update(
    db: Session, token_hash: str, purpose: OneTimeTokenPurpose
) -> OneTimeToken | None:
    stmt = (
        select(OneTimeToken)
        .where(OneTimeToken.token_hash == token_hash, OneTimeToken.purpose == purpose)
        .with_for_update()
    )
    return db.scalars(stmt).first()


def invalidate_one_time_tokens(
    db: Session, user_id: uuid.UUID, purpose: OneTimeTokenPurpose, now: datetime
) -> None:
    """Rend inutilisables les anciens liens quand un nouveau est envoyé."""
    db.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user_id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
