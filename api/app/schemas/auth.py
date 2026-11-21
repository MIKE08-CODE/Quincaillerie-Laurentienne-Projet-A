"""Schémas d'entrée et de sortie de l'authentification.

Ils servent à la fois à VALIDER les requêtes et à DOCUMENTER l'API : les `description` et
`examples` apparaissent dans Swagger (/docs).

Choix de sécurité :
- `extra="forbid"` : un champ inconnu (p. ex. `"role": "admin"`) est refusé au lieu d'être ignoré,
  ce qui bloque les tentatives d'attribution de privilèges par la requête.
- Les mots de passe sont des `SecretStr` : ils n'apparaissent jamais en clair dans un journal.
- Les espaces sont retirés des noms et du courriel, mais JAMAIS des mots de passe : « secret »
  et « secret  » sont deux mots de passe différents, l'API ne doit pas en modifier un en silence.
"""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, SecretStr, StringConstraints

from app.models import UserRole

EXAMPLE_PASSWORD = "Rivière-Pelle-Écrou-42"  # noqa: S105 — exemple affiché dans Swagger  # nosec B105


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


Email = Annotated[
    EmailStr,
    BeforeValidator(_strip),
    Field(description="Adresse courriel (insensible à la casse).", examples=["marie.gagnon@example.com"]),
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Password = Annotated[
    SecretStr,
    # Borne anti-abus seulement : la vraie règle (12 à 128 caractères) est vérifiée par la politique
    # de mot de passe, qui renvoie un message clair.
    Field(max_length=1024, examples=[EXAMPLE_PASSWORD]),
]
OneTimeTokenField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
    Field(description="Jeton reçu par courriel (partie du lien située après `#token=`)."),
]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Entrées
# ---------------------------------------------------------------------------
class RegisterRequest(_Input):
    email: Email
    password: Password = Field(
        description="Au moins 12 caractères, absent de la liste des mots de passe courants, "
        "sans le courriel ni le nom.",
    )
    first_name: Name = Field(description="Prénom.", examples=["Marie"])
    last_name: Name = Field(description="Nom de famille.", examples=["Gagnon"])
    language: Literal["fr", "en"] = Field(
        default="fr", description="Langue préférée pour les courriels et l'interface."
    )
    accept_privacy_policy: Literal[True] = Field(
        description="Consentement explicite à la politique de confidentialité (Loi 25). "
        "Doit valoir `true`, sinon l'inscription est refusée.",
    )
    marketing_opt_in: bool = Field(
        default=False, description="Accepte de recevoir des courriels promotionnels (facultatif)."
    )


class LoginRequest(_Input):
    email: Email
    password: Password = Field(description="Mot de passe du compte.")


class EmailRequest(_Input):
    email: Email


class TokenRequest(_Input):
    token: OneTimeTokenField


class ResetPasswordRequest(_Input):
    token: OneTimeTokenField
    new_password: Password = Field(description="Nouveau mot de passe (mêmes règles qu'à l'inscription).")


class MfaCodeRequest(_Input):
    code: str = Field(
        pattern=r"^\d{6}$",
        description="Code à 6 chiffres affiché par l'application d'authentification.",
        examples=["123456"],
    )


class MfaVerifyRequest(MfaCodeRequest):
    mfa_token: str = Field(
        min_length=1,
        max_length=2048,
        description="Jeton `mfa_token` reçu de `/auth/login` (valide 5 minutes).",
    )


# ---------------------------------------------------------------------------
# Sorties
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    """Session ouverte. Le jeton de rafraîchissement n'est PAS ici : il voyage seulement dans le
    cookie httpOnly `ql_refresh`, illisible par JavaScript."""

    access_token: str = Field(
        description="Jeton d'accès (JWT) à envoyer dans l'en-tête `Authorization: Bearer <jeton>`."
    )
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — type OAuth2 standard
    expires_in: int = Field(description="Durée de vie du jeton d'accès, en secondes (900 = 15 min).")
    mfa_setup_required: bool = Field(
        default=False,
        description="`true` pour le personnel qui n'a pas encore configuré la MFA : ce jeton ne permet "
        "que d'appeler `/auth/mfa/setup` puis `/auth/mfa/enable`.",
    )


class MfaChallengeResponse(BaseModel):
    """Mot de passe correct, mais la MFA est activée : il faut encore un code TOTP."""

    mfa_required: Literal[True] = True
    mfa_token: str = Field(description="À renvoyer à `/auth/mfa/verify` avec le code, dans les 5 minutes.")


class MfaSetupResponse(BaseModel):
    secret: str = Field(description="Secret TOTP à saisir manuellement si le code QR ne peut être lu.")
    otpauth_uri: str = Field(
        description="Adresse `otpauth://` à afficher sous forme de code QR (Google Authenticator, "
        "Microsoft Authenticator…)."
    )


class MessageResponse(BaseModel):
    message: str = Field(description="Message à afficher à l'utilisateur.")


class UserResponse(BaseModel):
    """Profil de l'utilisateur connecté. Aucun champ sensible (empreinte, secret MFA, compteurs)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identifiant unique de l'utilisateur.")
    email: str = Field(description="Courriel (toujours en minuscules).")
    first_name: str = Field(description="Prénom.")
    last_name: str = Field(description="Nom de famille.")
    language: str = Field(description="Langue préférée : `fr` ou `en`.")
    role: UserRole = Field(description="`client`, `clerk` (commis), `manager` (gérant) ou `admin`.")
    is_email_verified: bool = Field(description="Un compte non vérifié ne peut pas passer de commande.")
    mfa_enabled: bool = Field(description="`true` si l'authentification multifacteur est activée.")
    store_ids: list[uuid.UUID] = Field(description="Magasins auxquels le commis ou le gérant est affecté.")


class ErrorDetail(BaseModel):
    code: str = Field(
        description="Code stable, à traduire côté client (FR/EN).", examples=["invalid_credentials"]
    )
    message: str = Field(description="Message par défaut, en français.")


class ErrorResponse(BaseModel):
    """Format de TOUTES les erreurs de l'API. Les erreurs 422 ajoutent une liste `errors`
    (champ fautif + raison), sans jamais recopier la valeur envoyée."""

    detail: ErrorDetail
