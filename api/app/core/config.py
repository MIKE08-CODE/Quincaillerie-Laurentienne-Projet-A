"""Configuration de l'API, lue depuis les variables d'environnement et le fichier `.env`.

Aucun secret n'est écrit dans le code (ENF-02) : `SECRET_KEY` et `DATABASE_URL` n'ont pas de
valeur par défaut, l'application refuse donc de démarrer s'ils sont absents.
"""

import re
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

    # --- Courriels transactionnels (A-AUTH-01, A-AUTH-04) ---
    # console : affichés dans le terminal (développement seulement : ils contiennent des jetons);
    # memory : gardés en mémoire (tests); brevo : API HTTPS de Brevo (le SMTP sortant est bloqué
    # sur l'offre gratuite de Render); disabled : aucun envoi, journalisé sans jeton ni lien.
    # Non renseigné : console en développement, memory en test, disabled en production.
    email_backend: Literal["console", "memory", "brevo", "disabled"] | None = None
    email_from_address: str = ""  # expéditeur vérifié chez le fournisseur
    email_from_name: str = "Quincaillerie Laurentienne"
    brevo_api_key: SecretStr | None = None

    # --- Téléversement des images de produits (A-ADM-01) ---
    # disabled : téléversement refusé (503) tant qu'aucun stockage persistant n'est choisi;
    # memory : gardées en mémoire (tests seulement); cloudinary : API HTTPS de Cloudinary (ADR-009).
    # Le disque de Render est éphémère : il n'est jamais utilisé pour stocker des fichiers.
    # Non renseigné : memory en test, disabled ailleurs.
    image_storage_backend: Literal["disabled", "memory", "cloudinary"] | None = None
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: SecretStr | None = None
    cloudinary_api_secret: SecretStr | None = None
    cloudinary_folder: str = "quincaillerie-laurentienne"
    image_max_bytes: int = Field(default=5 * 1024 * 1024, ge=10_000, le=10 * 1024 * 1024)
    image_max_dimension: int = Field(default=6000, ge=100, le=10_000)  # pixels, par côté

    # --- Adresse IP du client pour la limitation de débit (ENF-05) ---
    # Vide (défaut) : adresse de la connexion TCP; AUCUN en-tête de proxy n'est cru.
    # Sinon : nom d'UN en-tête écrit par un relais de confiance qui écrase la valeur envoyée par le
    # client (p. ex. « cf-connecting-ip » derrière Cloudflare). X-Forwarded-For est refusé : les
    # relais y AJOUTENT des adresses, si bien que sa première valeur peut être inventée par le client.
    client_ip_header: str = ""

    @property
    def effective_email_backend(self) -> str:
        if self.email_backend is not None:
            return self.email_backend
        return {"development": "console", "test": "memory"}.get(self.app_env, "disabled")

    @property
    def effective_image_storage_backend(self) -> str:
        if self.image_storage_backend is not None:
            return self.image_storage_backend
        return "memory" if self.app_env == "test" else "disabled"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _check_client_ip_header(self) -> "Settings":
        header = self.client_ip_header.strip().lower()
        if header and not re.fullmatch(r"[a-z0-9-]{1,64}", header):
            raise ValueError("CLIENT_IP_HEADER doit être un nom d'en-tête HTTP simple.")
        if header in {"x-forwarded-for", "forwarded"}:
            raise ValueError(
                "CLIENT_IP_HEADER ne peut pas être X-Forwarded-For ni Forwarded (valeurs falsifiables)."
            )
        self.client_ip_header = header
        return self

    @model_validator(mode="after")
    def _check_email_settings(self) -> "Settings":
        if self.effective_email_backend == "brevo":
            if self.brevo_api_key is None or not self.brevo_api_key.get_secret_value().strip():
                raise ValueError("BREVO_API_KEY est obligatoire avec EMAIL_BACKEND=brevo.")
            if "@" not in self.email_from_address:
                raise ValueError(
                    "EMAIL_FROM_ADDRESS (expéditeur vérifié) est obligatoire avec EMAIL_BACKEND=brevo."
                )
        return self

    @model_validator(mode="after")
    def _check_image_storage_settings(self) -> "Settings":
        if self.effective_image_storage_backend != "cloudinary":
            return self
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.cloudinary_cloud_name.strip()):
            raise ValueError("CLOUDINARY_CLOUD_NAME est obligatoire (lettres minuscules, chiffres, - ou _).")
        for name in ("cloudinary_api_key", "cloudinary_api_secret"):
            value = getattr(self, name)
            if value is None or not value.get_secret_value().strip():
                raise ValueError(f"{name.upper()} est obligatoire avec IMAGE_STORAGE_BACKEND=cloudinary.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.cloudinary_folder):
            raise ValueError("CLOUDINARY_FOLDER doit être un nom de dossier simple.")
        self.cloudinary_cloud_name = self.cloudinary_cloud_name.strip()
        return self

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        """Bloque le démarrage en production si la configuration n'est pas sécuritaire."""
        if not self.is_production:
            return self
        if self.effective_email_backend in {"console", "memory"}:
            raise ValueError(
                "EMAIL_BACKEND console/memory interdit en production (jetons dans les journaux)."
            )
        if self.effective_image_storage_backend == "memory":
            raise ValueError("IMAGE_STORAGE_BACKEND=memory interdit en production (images perdues).")
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
