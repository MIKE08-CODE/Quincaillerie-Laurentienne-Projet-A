"""Primitives de sécurité : hachage des mots de passe, jetons, chiffrement, TOTP.

Ce fichier ne connaît ni HTTP ni la base de données : il ne fait que de la cryptographie.
"""

import hashlib
import hmac
import secrets
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Mots de passe — Argon2id (A-AUTH-03, ENF-02)
# ---------------------------------------------------------------------------
# PasswordHasher utilise Argon2id par défaut, avec les paramètres recommandés par la RFC 9106.
_password_hasher = PasswordHasher()

# Empreinte d'un mot de passe bidon, utilisée quand le courriel n'existe pas : la connexion prend
# alors autant de temps qu'avec un vrai compte, ce qui empêche de deviner les comptes au chronomètre.
_DUMMY_HASH = _password_hasher.hash(secrets.token_urlsafe(32))


def normalize_password(password: str) -> str:
    """Normalisation Unicode NFKC (recommandée par le NIST SP 800-63B).

    Un « é » peut être envoyé comme un seul caractère (Windows, Android) ou comme « e » + accent
    (macOS, iOS). Sans normalisation, le même mot de passe donnerait deux empreintes différentes
    et l'utilisateur ne pourrait plus se connecter depuis un autre appareil.
    """
    return unicodedata.normalize("NFKC", password)


def hash_password(password: str) -> str:
    return _password_hasher.hash(normalize_password(password))


def verify_password(password: str, password_hash: str | None) -> bool:
    """Vérifie un mot de passe. Prend un temps constant même si l'utilisateur n'existe pas."""
    try:
        valid = _password_hasher.verify(password_hash or _DUMMY_HASH, normalize_password(password))
        return valid and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Vrai si les paramètres Argon2 ont été renforcés depuis la création de l'empreinte."""
    return _password_hasher.check_needs_rehash(password_hash)


# ---------------------------------------------------------------------------
# Jetons opaques (rafraîchissement, vérification du courriel, réinitialisation)
# ---------------------------------------------------------------------------
def generate_opaque_token() -> str:
    """256 bits aléatoires, impossibles à deviner."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Empreinte SHA-256 stockée en base. Un jeton aléatoire de 256 bits n'a pas besoin d'Argon2."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# JWT d'accès (A-AUTH-02) et de défi MFA (A-AUTH-06)
# ---------------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
TokenType = Literal["access", "mfa_challenge"]


class InvalidTokenError(Exception):
    """Jeton absent, mal formé, mal signé, expiré ou du mauvais type."""


def _now() -> datetime:
    return datetime.now(UTC)


def create_jwt(subject: uuid.UUID, token_type: TokenType, expires_in: timedelta, **claims: Any) -> str:
    now = _now()
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
        **claims,
    }
    return jwt.encode(payload, get_settings().secret_key.get_secret_value(), algorithm=JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, *, mfa: bool) -> str:
    """Jeton d'accès de 15 min au plus. `mfa` indique si la MFA a été complétée pour cette session.

    Le rôle n'est volontairement PAS mis dans le jeton : il est relu en base à chaque requête,
    donc un changement de rôle ou une désactivation s'applique immédiatement.
    """
    minutes = get_settings().access_token_expire_minutes
    return create_jwt(user_id, "access", timedelta(minutes=minutes), mfa=mfa)


def create_mfa_challenge_token(user_id: uuid.UUID) -> str:
    """Jeton de quelques minutes prouvant que le mot de passe est bon, en attente du code TOTP."""
    minutes = get_settings().mfa_challenge_expire_minutes
    return create_jwt(user_id, "mfa_challenge", timedelta(minutes=minutes))


def issued_before(payload: dict[str, Any], moment: datetime | None) -> bool:
    """Vrai si le jeton a été émis avant `moment` (p. ex. avant un changement de mot de passe).

    `iat` est en secondes entières : on compare à la seconde près, sinon un jeton émis juste
    après le changement, dans la même seconde, serait refusé à tort.
    """
    return moment is not None and int(payload["iat"]) < int(moment.timestamp())


def decode_jwt(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Vérifie la signature, l'expiration et le type du jeton, puis renvoie son contenu."""
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],  # liste fixe : refuse l'attaque « alg: none »
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except jwt.PyJWTError as exc:  # signature invalide, expiré (→ 401), mal formé...
        raise InvalidTokenError from exc
    if payload.get("type") != expected_type:
        # Empêche d'utiliser un jeton de défi MFA comme jeton d'accès, et inversement.
        raise InvalidTokenError
    return payload


# ---------------------------------------------------------------------------
# Chiffrement du secret MFA (annexe D, A02)
# ---------------------------------------------------------------------------
def _fernet() -> Fernet:
    return Fernet(get_settings().mfa_encryption_key.get_secret_value().encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


# ---------------------------------------------------------------------------
# TOTP (A-AUTH-06)
# ---------------------------------------------------------------------------
TOTP_ISSUER = "Quincaillerie Laurentienne"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str) -> str:
    """Adresse `otpauth://` à afficher en code QR dans l'application d'authentification."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str, last_used_step: int | None) -> int | None:
    """Vérifie un code TOTP et renvoie son pas de temps, ou None s'il est refusé.

    Accepte le pas courant et ses voisins (±30 s de décalage d'horloge), mais refuse tout pas
    déjà utilisé : un code intercepté ne peut donc pas être rejoué.
    """
    totp = pyotp.TOTP(secret)
    current_step = totp.timecode(_now())
    for step in (current_step - 1, current_step, current_step + 1):
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None
