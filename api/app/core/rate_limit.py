"""Limitation de débit par adresse IP (ENF-05, A-AUTH-07) avec slowapi.

Elle protège contre les robots qui essaient beaucoup de comptes depuis une même adresse.
Le verrouillage par compte, lui, est dans auth_service (il protège un compte précis).

Limites de ce stockage en mémoire : chaque processus a ses propres compteurs. Avec plusieurs
instances en production, il faudra un stockage partagé (Redis) via `storage_uri`.
Derrière un proxy (Render, Azure), lancer uvicorn avec `--proxy-headers` pour obtenir la vraie IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limit_enabled)

# Limites des points de terminaison sensibles.
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/minute"
PASSWORD_FORGOT_LIMIT = "5/minute"  # noqa: S105 — une limite, pas un mot de passe
TOKEN_SUBMIT_LIMIT = "10/minute"  # noqa: S105 — vérif. courriel, réinitialisation, codes MFA
REFRESH_LIMIT = "30/minute"
