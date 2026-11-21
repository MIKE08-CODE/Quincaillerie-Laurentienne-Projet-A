"""Limitation de débit par adresse IP (ENF-05, A-AUTH-07) avec slowapi.

Elle protège contre les robots qui essaient beaucoup de comptes depuis une même adresse.
Le verrouillage par compte, lui, est dans auth_service (il protège un compte précis).

Limites de ce stockage en mémoire : chaque processus a ses propres compteurs. Avec plusieurs
instances en production, il faudra un stockage partagé (Redis) via `storage_uri`.

Adresse du client : par défaut, l'adresse de la connexion TCP. Les en-têtes de proxy ne sont JAMAIS
crus par défaut (uvicorn est lancé sans `--proxy-headers`) : un client pourrait sinon inventer
`X-Forwarded-For` pour obtenir un nouveau compteur à chaque requête. Derrière un relais qui ÉCRASE un
en-tête dédié (Cloudflare devant Render : `CF-Connecting-IP`), configurer `CLIENT_IP_HEADER`; la valeur
n'est retenue que si c'est une adresse IP valide.
"""

import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """Clé de la limitation de débit : en-tête de confiance configuré, sinon adresse de la connexion."""
    header = get_settings().client_ip_header
    if header:
        value = request.headers.get(header, "").strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass  # en-tête absent ou invalide : on retombe sur l'adresse de la connexion
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, enabled=get_settings().rate_limit_enabled)

# Limites des points de terminaison sensibles.
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/minute"
PASSWORD_FORGOT_LIMIT = "5/minute"  # noqa: S105 — une limite, pas un mot de passe  # nosec B105
TOKEN_SUBMIT_LIMIT = "10/minute"  # noqa: S105 — courriel, réinitialisation, codes MFA  # nosec B105
REFRESH_LIMIT = "30/minute"
PUBLIC_READ_LIMIT = "120/minute"  # lecture publique du catalogue (contrat §5)
