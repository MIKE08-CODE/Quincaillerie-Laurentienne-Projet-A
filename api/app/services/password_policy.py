"""Politique de mot de passe (A-AUTH-03).

- au moins 12 caractères (et au plus 128, pour éviter les abus);
- absent de la liste des mots de passe courants;
- ne contient pas le courriel, le nom ni le nom de l'entreprise.

On ne force PAS de mélange majuscules/chiffres/symboles : les recommandations actuelles
(NIST SP 800-63B) privilégient la longueur et le refus des mots de passe connus.
"""

from functools import lru_cache
from pathlib import Path

from app.core.errors import ValidationFailed
from app.core.security import normalize_password

MIN_LENGTH = 12
MAX_LENGTH = 128
_COMMON_PASSWORDS_FILE = Path(__file__).resolve().parents[1] / "core" / "data" / "common_passwords.txt"
_CONTEXT_WORDS = ("quincaillerie", "laurentienne")


@lru_cache
def _common_passwords() -> frozenset[str]:
    """Chargée une seule fois en mémoire, au premier appel."""
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def validate_password(password: str, *, email: str = "", first_name: str = "", last_name: str = "") -> None:
    """Lève ValidationFailed avec un message clair si le mot de passe est trop faible.

    Les règles s'appliquent au mot de passe normalisé, c'est-à-dire à ce qui sera réellement haché.
    """
    password = normalize_password(password)
    if len(password) < MIN_LENGTH:
        raise ValidationFailed(
            "password_too_short", f"Le mot de passe doit contenir au moins {MIN_LENGTH} caractères."
        )
    if len(password) > MAX_LENGTH:
        raise ValidationFailed(
            "password_too_long", f"Le mot de passe doit contenir au plus {MAX_LENGTH} caractères."
        )

    lowered = password.lower()
    if lowered in _common_passwords():
        raise ValidationFailed(
            "password_too_common",
            "Ce mot de passe est trop courant et facile à deviner. Choisissez-en un autre.",
        )

    if len(set(lowered)) <= 2:  # p. ex. « aaaaaaaaaaaa » ou « abababababab »
        raise ValidationFailed(
            "password_too_simple", "Le mot de passe est trop répétitif. Choisissez-en un autre."
        )

    local_part = email.split("@")[0].lower()
    personal = [w.lower() for w in (local_part, first_name, last_name) if len(w) >= 3]
    if any(word in lowered for word in (*personal, *_CONTEXT_WORDS)):
        raise ValidationFailed(
            "password_contains_personal_info",
            "Le mot de passe ne doit pas contenir votre courriel, votre nom ni le nom du magasin.",
        )
