"""Authentification multifacteur TOTP (A-AUTH-06).

Parcours du personnel :
1. Première connexion : mot de passe → session limitée (mfa=false) → /mfa/setup → /mfa/enable
   avec un premier code → session complète (mfa=true).
2. Connexions suivantes : mot de passe → jeton de défi → /mfa/verify avec le code → session complète.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import security, security_log
from app.core.errors import AppError, Conflict, Unauthorized
from app.models import User
from app.repositories import user_repository
from app.services import auth_service

INVALID_CODE = ("invalid_mfa_code", "Code de vérification invalide.")


@dataclass(frozen=True)
class MfaSetup:
    secret: str
    otpauth_uri: str


def setup(db: Session, user: User) -> MfaSetup:
    """Génère un nouveau secret (non actif tant qu'un premier code n'a pas été confirmé)."""
    if user.mfa_enabled:
        raise Conflict("mfa_already_enabled", "L'authentification multifacteur est déjà activée.")
    secret = security.generate_totp_secret()
    user.mfa_secret_encrypted = security.encrypt_secret(secret)
    user.mfa_last_used_step = None
    db.commit()
    return MfaSetup(secret=secret, otpauth_uri=security.totp_provisioning_uri(secret, user.email))


def _check_code(user: User, code: str) -> bool:
    """Vérifie le code et retient son pas de temps pour empêcher qu'il soit rejoué."""
    if not user.mfa_secret_encrypted:
        return False
    step = security.verify_totp(
        security.decrypt_secret(user.mfa_secret_encrypted), code, user.mfa_last_used_step
    )
    if step is None:
        return False
    user.mfa_last_used_step = step
    return True


def enable(db: Session, user: User, code: str) -> auth_service.AuthSession:
    """Confirme la configuration avec un premier code, puis ouvre une session complète."""
    user = user_repository.lock_by_id(db, user.id)
    if user.mfa_enabled:
        raise Conflict("mfa_already_enabled", "L'authentification multifacteur est déjà activée.")
    if not user.mfa_secret_encrypted:
        raise AppError("mfa_setup_required", "Configurez d'abord l'authentification multifacteur.")
    auth_service.ensure_not_locked(user)
    if not _check_code(user, code):
        # Compté comme un échec de connexion : sinon on pourrait essayer les 1 000 000 de codes.
        auth_service.register_failed_attempt(user)
        db.commit()
        security_log.security_event(security_log.MFA_FAILED, user.id, step="enable")
        raise Unauthorized(*INVALID_CODE)
    user.mfa_enabled = True
    auth_service.reset_failed_attempts(user)
    session = auth_service.open_session(db, user, mfa_verified=True)
    db.commit()
    security_log.security_event(security_log.MFA_ENABLED, user.id)
    return session


def verify_challenge(db: Session, mfa_token: str, code: str) -> auth_service.AuthSession:
    """Deuxième étape de la connexion. Les mauvais codes comptent dans le verrouillage (A-AUTH-07)."""
    try:
        payload = security.decode_jwt(mfa_token, "mfa_challenge")
    except security.InvalidTokenError:
        raise Unauthorized(
            "invalid_mfa_token", "Session de vérification expirée. Reconnectez-vous."
        ) from None

    user = user_repository.lock_by_id(db, uuid.UUID(payload["sub"]))
    if (
        user is None
        or not user.is_active
        or not user.mfa_enabled
        # Défi obtenu avant une réinitialisation du mot de passe : l'ancien mot de passe ne compte plus.
        or security.issued_before(payload, user.tokens_valid_after)
    ):
        raise Unauthorized("invalid_mfa_token", "Session de vérification expirée. Reconnectez-vous.")
    auth_service.ensure_not_locked(user)

    if not _check_code(user, code):
        auth_service.register_failed_attempt(user)
        db.commit()
        security_log.security_event(security_log.MFA_FAILED, user.id, step="verify")
        raise Unauthorized(*INVALID_CODE)

    auth_service.reset_failed_attempts(user)
    session = auth_service.open_session(db, user, mfa_verified=True)
    db.commit()
    return session
