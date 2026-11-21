"""Envoi des courriels de l'authentification.

Pour l'instant, les courriels ne sont pas réellement envoyés :
- en développement, ils sont affichés dans la console pour pouvoir cliquer sur le lien;
- en test, ils sont gardés dans `outbox` pour que les tests lisent le lien reçu.
Un vrai fournisseur (SMTP, SendGrid…) remplacera `_deliver` au déploiement.

Les liens contiennent un jeton secret : ils ne doivent jamais passer par le logger (ENF-13).
"""

from dataclasses import dataclass

from app.core.config import get_settings


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


def _deliver(message: EmailMessage) -> None:
    settings = get_settings()
    if settings.app_env == "test":
        outbox.append(message)
    elif settings.app_env == "development":
        print(
            f"\n--- COURRIEL (dev) à {message.to} ---\n{message.subject}\n\n{message.body}\n---\n", flush=True
        )
    else:
        raise NotImplementedError("Configurer un fournisseur de courriel pour la production.")


def _send(template: str, to: str, language: str, link: str = "") -> None:
    subject, body = _TEXTS[template].get(language, _TEXTS[template]["fr"])
    _deliver(EmailMessage(to=to, subject=subject, body=body.format(link=link)))


# Le jeton est placé après « # » : le navigateur ne l'envoie jamais au serveur web, il ne finit
# donc ni dans les journaux du serveur ni dans l'en-tête Referer. Le web le lit dans location.hash.
def send_verification_email(to: str, language: str, token: str) -> None:
    _send("verify", to, language, f"{get_settings().web_base_url}/verifier-courriel#token={token}")


def send_already_registered_email(to: str, language: str) -> None:
    _send("already_registered", to, language)


def send_password_reset_email(to: str, language: str, token: str) -> None:
    _send("reset", to, language, f"{get_settings().web_base_url}/reinitialiser-mot-de-passe#token={token}")
