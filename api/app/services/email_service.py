"""Envoi des courriels de l'authentification (A-AUTH-01, A-AUTH-04).

Modes (`EMAIL_BACKEND`, voir app/core/config.py) :
- `console` : affichés dans le terminal (développement seulement);
- `memory` : gardés dans `outbox` (tests);
- `brevo` : API HTTPS transactionnelle de Brevo (le SMTP sortant est bloqué sur l'offre gratuite de
  Render; une API HTTPS fonctionne);
- `disabled` : aucun envoi (défaut en production sans fournisseur).

Robustesse : un envoi raté ne lève JAMAIS d'exception. Ces fonctions s'exécutent dans des tâches
d'arrière-plan, après la réponse HTTP : une exception y coupait la connexion. L'échec est journalisé.

Confidentialité (ENF-13) : les liens contiennent un jeton secret. Les journaux ne contiennent jamais
le lien, le jeton, le corps du message ni l'adresse du destinataire : seulement le modèle et la cause.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger("app.email")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SEND_TIMEOUT_SECONDS = 10


class EmailDeliveryError(Exception):
    """Le fournisseur a refusé le message (cause sans donnée personnelle)."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


outbox: list[EmailMessage] = []

_TEXTS = {
    "verify": {
        "fr": (
            "Confirmez votre courriel",
            "Bienvenue! Confirmez votre courriel avec ce lien (valide 24 h) :\n{link}",
        ),
        "en": ("Confirm your email", "Welcome! Confirm your email with this link (valid 24 h):\n{link}"),
    },
    "already_registered": {
        "fr": (
            "Tentative d'inscription",
            "Quelqu'un a essayé de créer un compte avec votre courriel. Si c'est vous, connectez-vous "
            "ou réinitialisez votre mot de passe. Sinon, ignorez ce message.",
        ),
        "en": (
            "Sign-up attempt",
            "Someone tried to create an account with your email. If it was you, sign in or reset "
            "your password. Otherwise, you can ignore this message.",
        ),
    },
    "reset": {
        "fr": (
            "Réinitialisation du mot de passe",
            "Réinitialisez votre mot de passe avec ce lien (valide 30 min, utilisable une seule fois) :"
            "\n{link}\nSi vous n'avez rien demandé, ignorez ce message.",
        ),
        "en": (
            "Password reset",
            "Reset your password with this link (valid 30 min, single use):\n{link}\n"
            "If you did not request this, ignore this message.",
        ),
    },
}


def _send_with_brevo(message: EmailMessage) -> None:
    settings = get_settings()
    payload = {
        "sender": {"name": settings.email_from_name, "email": settings.email_from_address},
        "to": [{"email": message.to}],
        "subject": message.subject,
        "textContent": message.body,
    }
    api_key = settings.brevo_api_key.get_secret_value() if settings.brevo_api_key else ""
    request = urllib.request.Request(  # noqa: S310 — URL https fixe, jamais fournie par l'utilisateur
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"accept": "application/json", "content-type": "application/json", "api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=SEND_TIMEOUT_SECONDS) as response:  # noqa: S310  # nosec B310
            status = response.status
    except urllib.error.HTTPError as exc:
        raise EmailDeliveryError(f"réponse HTTP {exc.code} du fournisseur") from None
    if status not in (200, 201, 202):
        raise EmailDeliveryError(f"réponse HTTP {status} du fournisseur")


def _deliver(template: str, message: EmailMessage) -> bool:
    """Envoie le message selon le mode configuré. Renvoie False si rien n'a été remis au fournisseur."""
    backend = get_settings().effective_email_backend
    try:
        if backend == "memory":
            outbox.append(message)
            return True
        if backend == "console":
            print(
                f"\n--- COURRIEL (dev) à {message.to} ---\n{message.subject}\n\n{message.body}\n---\n",
                flush=True,
            )
            return True
        if backend == "brevo":
            _send_with_brevo(message)
            return True
        logger.warning(
            "Courriel « %s » non envoyé : aucun fournisseur configuré (EMAIL_BACKEND=disabled).", template
        )
        return False
    except EmailDeliveryError as exc:
        logger.error("Échec de l'envoi du courriel « %s » : %s.", template, exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.error(
            "Échec de l'envoi du courriel « %s » : fournisseur injoignable (%s).",
            template,
            type(exc).__name__,
        )
    except Exception as exc:  # noqa: BLE001 — une tâche d'arrière-plan ne doit jamais couper la connexion
        logger.error("Échec inattendu de l'envoi du courriel « %s » (%s).", template, type(exc).__name__)
    return False


def _send(template: str, to: str, language: str, link: str = "") -> bool:
    subject, body = _TEXTS[template].get(language, _TEXTS[template]["fr"])
    return _deliver(template, EmailMessage(to=to, subject=subject, body=body.format(link=link)))


# Le jeton est placé après « # » : le navigateur ne l'envoie jamais au serveur web, il ne finit
# donc ni dans les journaux du serveur ni dans l'en-tête Referer. Le web le lit dans location.hash.
def send_verification_email(to: str, language: str, token: str) -> bool:
    return _send("verify", to, language, f"{get_settings().web_base_url}/verifier-courriel#token={token}")


def send_already_registered_email(to: str, language: str) -> bool:
    return _send("already_registered", to, language)


def send_password_reset_email(to: str, language: str, token: str) -> bool:
    return _send(
        "reset", to, language, f"{get_settings().web_base_url}/reinitialiser-mot-de-passe#token={token}"
    )
