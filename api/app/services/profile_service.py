"""Profil du client connecté (A-PRV-01) : nom, langue et préférence de communication.

Les fonctions reçoivent une session de base de données et des valeurs simples; elles ne
connaissent ni FastAPI ni HTTP (ENF-11). Elles valident la transaction (commit) elles-mêmes.

Préférence de communication (courriels promotionnels) : elle n'est PAS une colonne de `users`.
C'est un consentement daté et versionné dans `consents` (Loi 25) :
- activer = ajouter une ligne MARKETING (avec la version de la politique en vigueur);
- retirer = remplir `revoked_at` de la ligne en vigueur. On ne supprime jamais une ligne :
  l'historique sert de preuve.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Consent, ConsentType, User
from app.repositories import user_repository


def marketing_opt_in(db: Session, user: User) -> bool:
    """Vrai si l'utilisateur a un consentement MARKETING en vigueur (non retiré)."""
    return user_repository.get_active_consent(db, user.id, ConsentType.MARKETING) is not None


def update_profile(db: Session, user: User, changes: dict) -> User:
    """Applique une modification partielle du profil et la valide.

    `changes` ne contient que les champs envoyés par le client (`model_dump(exclude_unset=True)`) :
    un champ absent n'est pas modifié. Le courriel, le rôle et le mot de passe n'y figurent jamais
    (le schéma les refuse).
    """
    # Ligne verrouillée jusqu'au commit : deux modifications simultanées (p. ex. web et mobile) ne
    # peuvent pas créer deux consentements MARKETING en vigueur.
    locked = user_repository.lock_by_id(db, user.id) or user

    for field in ("first_name", "last_name", "language"):
        if field in changes:
            setattr(locked, field, changes[field])

    if "marketing_opt_in" in changes:
        _set_marketing_consent(db, locked, changes["marketing_opt_in"])

    db.commit()
    return locked


def _set_marketing_consent(db: Session, user: User, wanted: bool) -> None:
    """Accorde ou retire le consentement MARKETING. Sans effet si l'état est déjà celui demandé."""
    active = user_repository.get_active_consent(db, user.id, ConsentType.MARKETING)
    if wanted and active is None:
        user_repository.add_consent(
            db,
            Consent(
                user_id=user.id,
                type=ConsentType.MARKETING,
                version=get_settings().privacy_policy_version,
            ),
        )
    elif not wanted and active is not None:
        active.revoked_at = datetime.now(UTC)
