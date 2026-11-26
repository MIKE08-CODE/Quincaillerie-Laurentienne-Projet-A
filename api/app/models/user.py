"""Table `users` (cahier, section A.6) + colonnes nécessaires au verrouillage et à la MFA."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(enum.StrEnum):
    """Rôles stockés (A-AUTH-05). Le « visiteur » n'est pas stocké : c'est l'absence de jeton."""

    CLIENT = "client"
    CLERK = "clerk"  # commis
    MANAGER = "manager"  # gérant de magasin
    ADMIN = "admin"


# Le personnel et les administrateurs doivent utiliser la MFA (A-AUTH-06).
STAFF_ROLES = frozenset({UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN})


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Courriel unique sans tenir compte des majuscules (cahier A.6 : « index sur lower »).
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
        CheckConstraint("language IN ('fr', 'en')", name="language"),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254))
    # Empreinte Argon2id uniquement : le mot de passe en clair n'est jamais stocké (A-AUTH-03).
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,  # VARCHAR + contrainte CHECK : plus simple à faire évoluer
            create_constraint=True,
            values_callable=lambda roles: [r.value for r in roles],
            length=20,
        ),
        default=UserRole.CLIENT,
        server_default=UserRole.CLIENT.value,
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(
        String(2), default="fr", server_default="fr"
    )  # FR par défaut (ENF-10)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    # --- MFA TOTP (A-AUTH-06) ---
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(String(255))  # chiffré (Fernet)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Dernier pas de temps TOTP accepté : empêche de réutiliser deux fois le même code.
    mfa_last_used_step: Mapped[int | None] = mapped_column(Integer)

    # --- Verrouillage progressif (A-AUTH-07) ---
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Les jetons d'accès émis AVANT cette date sont refusés. Rempli lors d'une réinitialisation du
    # mot de passe : un jeton volé devient inutilisable immédiatement, sans attendre ses 15 minutes.
    tokens_valid_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store_assignments: Mapped[list["StaffAssignment"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def store_ids(self) -> list[uuid.UUID]:
        return [a.store_id for a in self.store_assignments]
