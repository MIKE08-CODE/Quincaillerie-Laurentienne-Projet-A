"""Configuration de l'API, lue depuis les variables d'environnement et le fichier `.env`.

Aucun secret n'est écrit dans le code (ENF-02) : `SECRET_KEY` et `DATABASE_URL` n'ont pas de
valeur par défaut, l'application refuse donc de démarrer s'ils sont absents.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/app/core/config.py -> parents[3] = racine du dépôt, où se trouve le `.env` partagé.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Valeurs d'exemple de `.env.example` qui ne doivent jamais servir en production.
_PLACEHOLDER_SECRETS = {"change-me", "changeme", "secret", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # le `.env` contient aussi les variables du web, du mobile et du RAG
    )

    app_env: Literal["development", "test", "production"] = "development"

    # SecretStr : la valeur n'apparaît jamais dans un `print(settings)` ni dans les journaux.
    secret_key: SecretStr
    database_url: SecretStr

    # Clé Fernet qui chiffre les secrets MFA en base (annexe D, A02 : clé hors de la BD).
    # Générer avec : python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    mfa_encryption_key: SecretStr

    # --- Jetons (A-AUTH-02) ---
    # Le cahier exige un jeton d'accès de 15 minutes au plus : on l'impose ici.
    access_token_expire_minutes: int = Field(default=15, ge=1, le=15)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    # Durée maximale d'une session, même si elle est rafraîchie sans arrêt (OWASP A07).
    session_max_days: int = Field(default=30, ge=1, le=90)
    # "strict" si le web et l'API partagent le même site; "none" s'ils sont sur deux domaines
    # différents en production (le cookie reste alors httpOnly + Secure).
    refresh_cookie_samesite: Literal["strict", "lax", "none"] = "strict"

    # --- Jetons à usage unique ---
    email_verification_expire_hours: int = 24
    password_reset_expire_minutes: int = Field(default=30, ge=5, le=30)  # A-AUTH-04 : 30 min
    mfa_challenge_expire_minutes: int = 5

    # --- Verrouillage progressif (A-AUTH-07) ---
    login_max_failures: int = 5  # 5 échecs ...
    login_lockout_minutes: int = 15  # ... blocage de 15 min (doublé à chaque nouveau palier)

    # --- Limitation de débit par IP (ENF-05) ---
    rate_limit_enabled: bool = True

    # Version de la politique de confidentialité acceptée à l'inscription (A-AUTH-01, Loi 25).
    privacy_policy_version: str = "1.0"

    # Adresse de l'application web, utilisée dans les liens envoyés par courriel.
    web_base_url: str = "http://localhost:5173"

    # Origines autorisées par CORS, séparées par des virgules (ENF-03).
    cors_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        """Bloque le démarrage en production si la configuration n'est pas sécuritaire."""
        if not self.is_production:
            return self
        key = self.secret_key.get_secret_value()
        if key.lower() in _PLACEHOLDER_SECRETS or len(key) < 32:
            raise ValueError("SECRET_KEY doit être une valeur aléatoire d'au moins 32 caractères.")
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS ne doit pas contenir '*' en production.")
        if not self.rate_limit_enabled:
            raise ValueError("La limitation de débit ne peut pas être désactivée en production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Charge la configuration une seule fois, puis la réutilise."""
    return Settings()
