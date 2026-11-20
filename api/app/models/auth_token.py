"""Jetons de l'authentification. Seule l'empreinte SHA-256 est stockée, jamais le jeton lui-même :
si la base fuit, les jetons volés sont inutilisables.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RefreshToken(Base):
    """Jeton de rafraîchissement (A-AUTH-02). Révocable : déconnexion, rotation, vol détecté."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # La session a-t-elle complété la MFA? Recopié dans chaque nouveau jeton d'accès.
    mfa_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Expiration de CE jeton (7 jours, repoussée à chaque rafraîchissement)...
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # ...mais jamais au-delà de la fin ABSOLUE de la session (30 jours après la connexion),
    # recopiée d'un jeton au suivant : il faut se reconnecter au moins une fois par mois.
    session_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OneTimeTokenPurpose(str, enum.Enum):
    EMAIL_VERIFICATION = "email_verification"  # A-AUTH-01
    PASSWORD_RESET = "password_reset"  # noqa: S105 — nom d'usage (A-AUTH-04), pas un secret  # nosec B105


class OneTimeToken(Base):
    """Jeton à usage unique envoyé par courriel. `used_at` rempli = jeton consommé."""

    __tablename__ = "one_time_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[OneTimeTokenPurpose] = mapped_column(
        Enum(
            OneTimeTokenPurpose,
            name="one_time_token_purpose",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda purposes: [p.value for p in purposes],
            length=30,
        )
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
