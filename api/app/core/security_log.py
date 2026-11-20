"""Journal des événements de sécurité (annexe D, A09 : journalisation et surveillance).

Règle (ENF-13, Loi 25) : aucun renseignement personnel ni secret dans ces journaux.
On enregistre l'identifiant interne (UUID) de l'utilisateur, jamais son courriel, son nom,
un mot de passe ou un jeton. Le UUID permet d'enquêter sans exposer la personne.

Exemple de ligne produite :
    WARNING app.security event=account_locked user_id=5e32…  lock_minutes=15
"""

import logging
import uuid

logger = logging.getLogger("app.security")

# Événements à surveiller (niveau WARNING) : un pic peut signaler une attaque.
LOGIN_FAILED = "login_failed"
ACCOUNT_LOCKED = "account_locked"
REFRESH_TOKEN_REUSE = "refresh_token_reuse_detected"  # vol probable d'un jeton
MFA_FAILED = "mfa_failed"

# Événements normaux mais sensibles (niveau INFO), utiles pour reconstituer un incident.
PASSWORD_RESET_REQUESTED = "password_reset_requested"
PASSWORD_RESET_COMPLETED = "password_reset_completed"
MFA_ENABLED = "mfa_enabled"

_WARNINGS = {LOGIN_FAILED, ACCOUNT_LOCKED, REFRESH_TOKEN_REUSE, MFA_FAILED}


def security_event(event: str, user_id: uuid.UUID | None = None, **details: object) -> None:
    """Enregistre un événement. `details` ne doit contenir que des valeurs non personnelles."""
    level = logging.WARNING if event in _WARNINGS else logging.INFO
    extra = " ".join(f"{key}={value}" for key, value in details.items())
    logger.log(level, "event=%s user_id=%s %s", event, user_id or "-", extra)
