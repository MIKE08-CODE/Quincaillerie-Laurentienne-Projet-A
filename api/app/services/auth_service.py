"""Logique métier de l'authentification (A-AUTH-01, 02, 03, 04, 07).

Les fonctions reçoivent une session de base de données et des valeurs simples; elles ne
connaissent ni FastAPI ni HTTP. Elles valident la transaction (commit) elles-mêmes.
"""

import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security, security_log
from app.core.config import get_settings
from app.core.errors import AccountLocked, AppError, Unauthorized
from app.models import Consent, ConsentType, OneTimeToken, OneTimeTokenPurpose, RefreshToken, User, UserRole
from app.repositories import token_repository, user_repository
from app.services import email_service
from app.services.password_policy import validate_password

# Planifie une tâche après l'envoi de la réponse (BackgroundTasks.add_task de FastAPI).
# Les courriels partent ainsi en arrière-plan : la réponse prend le même temps, que le compte
# existe ou non, ce qui empêche de deviner les comptes au chronomètre.
Scheduler = Callable[..., Any]

MAX_LOCKOUT = timedelta(hours=24)
INVALID_CREDENTIALS = ("invalid_credentials", "Courriel ou mot de passe invalide.")


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True)
class AuthSession:
    """Jetons d'une session ouverte. `refresh_token` est None pour une session limitée."""

    access_token: str
    expires_in: int  # durée de vie du jeton d'accès, en secondes
    refresh_token: str | None
    refresh_expires_in: int = 0  # durée de vie du cookie, en secondes
    mfa_setup_required: bool = False


@dataclass(frozen=True)
class MfaChallenge:
    """Le mot de passe est bon, mais un code TOTP est encore exigé (A-AUTH-06)."""

    mfa_token: str


# ---------------------------------------------------------------------------
# Sessions et jetons (A-AUTH-02)
# ---------------------------------------------------------------------------
def open_session(
    db: Session, user: User, *, mfa_verified: bool, session_expires_at: datetime | None = None
) -> AuthSession:
    """Émet un jeton d'accès et un jeton de rafraîchissement (dont seule l'empreinte est gardée).

    `session_expires_at` : fin absolue de la session. Absente lors d'une connexion (on la calcule),
    recopiée lors d'un rafraîchissement (la session ne peut donc pas être prolongée à l'infini).
    """
    settings = get_settings()
    now = _now()
    session_expires_at = session_expires_at or now + timedelta(days=settings.session_max_days)
    expires_at = min(now + timedelta(days=settings.refresh_token_expire_days), session_expires_at)

    raw_refresh = security.generate_opaque_token()
    token_repository.add_refresh_token(
        db,
        RefreshToken(
            user_id=user.id,
            token_hash=security.hash_token(raw_refresh),
            mfa_verified=mfa_verified,
            expires_at=expires_at,
            session_expires_at=session_expires_at,
        ),
    )
    return AuthSession(
        access_token=security.create_access_token(user.id, mfa=mfa_verified),
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_token=raw_refresh,
        refresh_expires_in=int((expires_at - now).total_seconds()),
    )


def refresh_session(db: Session, raw_refresh: str | None) -> AuthSession:
    """Rotation : l'ancien jeton est révoqué et un nouveau est émis à chaque rafraîchissement.

    Si un jeton déjà révoqué est présenté, il a probablement été volé (le vrai propriétaire l'a
    déjà échangé) : toutes les sessions de l'utilisateur sont alors fermées (OWASP A07).
    """
    invalid = Unauthorized("invalid_refresh_token", "Session expirée. Veuillez vous reconnecter.")
    if not raw_refresh:
        raise invalid

    now = _now()
    stored = token_repository.get_refresh_token_for_update(db, security.hash_token(raw_refresh))
    if stored is None:
        raise invalid
    if stored.revoked_at is not None:
        token_repository.revoke_all_refresh_tokens(db, stored.user_id, now)
        db.commit()
        security_log.security_event(security_log.REFRESH_TOKEN_REUSE, stored.user_id)
        raise invalid
    if stored.expires_at <= now:
        raise invalid

    user = user_repository.get_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        stored.revoked_at = now
        db.commit()
        raise invalid

    stored.revoked_at = now
    session = open_session(
        db, user, mfa_verified=stored.mfa_verified, session_expires_at=stored.session_expires_at
    )
    db.commit()
    return session


def logout(db: Session, raw_refresh: str | None) -> None:
    """Révoque le jeton de rafraîchissement (A-AUTH-02). Ne révèle jamais s'il existait."""
    if not raw_refresh:
        return
    stored = token_repository.get_refresh_token_for_update(db, security.hash_token(raw_refresh))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = _now()
        db.commit()


# ---------------------------------------------------------------------------
# Inscription et vérification du courriel (A-AUTH-01)
# ---------------------------------------------------------------------------
def _create_one_time_token(db: Session, user: User, purpose: OneTimeTokenPurpose, lifetime: timedelta) -> str:
    now = _now()
    token_repository.invalidate_one_time_tokens(db, user.id, purpose, now)
    raw = security.generate_opaque_token()
    token_repository.add_one_time_token(
        db,
        OneTimeToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=security.hash_token(raw),
            expires_at=now + lifetime,
        ),
    )
    return raw


def _consume_one_time_token(db: Session, raw: str, purpose: OneTimeTokenPurpose) -> OneTimeToken:
    """Renvoie le jeton s'il est valide, et le marque comme utilisé (usage unique)."""
    stored = token_repository.get_one_time_token_for_update(db, security.hash_token(raw), purpose)
    now = _now()
    if stored is None or stored.used_at is not None or stored.expires_at <= now:
        raise AppError("invalid_or_expired_token", "Ce lien est invalide ou a expiré.")
    stored.used_at = now
    return stored


def register(
    db: Session,
    schedule: Scheduler,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    language: str,
    marketing_opt_in: bool = False,
) -> None:
    """Inscrit un CLIENT. Le rôle n'est jamais fourni par l'appelant : le personnel est créé
    uniquement par un administrateur (A-ADM-02).

    Réponse identique si le courriel est déjà utilisé : on prévient plutôt le propriétaire du
    compte par courriel, sans révéler à l'appelant que le compte existe.
    """
    settings = get_settings()
    email = normalize_email(email)
    # Validé AVANT de chercher le compte : un mot de passe faible donne la même erreur dans tous les cas.
    validate_password(password, email=email, first_name=first_name, last_name=last_name)
    # Haché AVANT de chercher le compte, même s'il ne servira pas : Argon2id prend ~100 ms, et le
    # sauter quand le courriel existe permettrait de deviner les comptes au chronomètre.
    password_hash = security.hash_password(password)

    existing = user_repository.get_by_email(db, email)
    if existing is not None:
        schedule(email_service.send_already_registered_email, existing.email, existing.language)
        return

    try:
        user = user_repository.add(
            db,
            User(
                email=email,
                password_hash=password_hash,
                role=UserRole.CLIENT,
                first_name=first_name,
                last_name=last_name,
                language=language,
            ),
        )
        # Preuve horodatée du consentement (CA d'A-AUTH-01, Loi 25).
        user_repository.add_consent(
            db, Consent(user_id=user.id, type=ConsentType.PRIVACY, version=settings.privacy_policy_version)
        )
        if marketing_opt_in:
            user_repository.add_consent(
                db,
                Consent(user_id=user.id, type=ConsentType.MARKETING, version=settings.privacy_policy_version),
            )
        token = _create_one_time_token(
            db,
            user,
            OneTimeTokenPurpose.EMAIL_VERIFICATION,
            timedelta(hours=settings.email_verification_expire_hours),
        )
        db.commit()
    except IntegrityError:
        # Deux inscriptions simultanées avec le même courriel : l'index unique a refusé la seconde.
        db.rollback()
        return

    schedule(email_service.send_verification_email, user.email, user.language, token)


def verify_email(db: Session, raw_token: str) -> None:
    """Confirme le courriel avec le jeton reçu par courriel (usage unique, 24 h)."""
    stored = _consume_one_time_token(db, raw_token, OneTimeTokenPurpose.EMAIL_VERIFICATION)
    user = user_repository.lock_by_id(db, stored.user_id)
    if user is not None and user.email_verified_at is None:
        user.email_verified_at = _now()
    db.commit()


def resend_verification(db: Session, schedule: Scheduler, email: str) -> None:
    """Renvoie le lien de vérification. Même réponse que le compte existe ou non."""
    user = user_repository.get_by_email(db, normalize_email(email))
    if user is None or not user.is_active or user.is_email_verified:
        return
    token = _create_one_time_token(
        db,
        user,
        OneTimeTokenPurpose.EMAIL_VERIFICATION,
        timedelta(hours=get_settings().email_verification_expire_hours),
    )
    db.commit()
    schedule(email_service.send_verification_email, user.email, user.language, token)


# ---------------------------------------------------------------------------
# Connexion et verrouillage progressif (A-AUTH-07)
# ---------------------------------------------------------------------------
def ensure_not_locked(user: User) -> None:
    """Lève AccountLocked (423) avec l'en-tête Retry-After si le compte est bloqué."""
    now = _now()
    if user.locked_until is not None and user.locked_until > now:
        seconds = math.ceil((user.locked_until - now).total_seconds())
        raise AccountLocked(
            "account_locked",
            "Trop de tentatives échouées. Réessayez plus tard.",
            headers={"Retry-After": str(seconds)},
        )


def register_failed_attempt(user: User) -> None:
    """Compte un échec. Tous les 5 échecs, le compte est bloqué : 15 min, puis 30, 60… (max 24 h)."""
    settings = get_settings()
    user.failed_login_count += 1
    over = user.failed_login_count - settings.login_max_failures
    if over >= 0 and over % settings.login_max_failures == 0:
        level = over // settings.login_max_failures  # 0 au 5e échec, 1 au 10e, 2 au 15e...
        duration = min(timedelta(minutes=settings.login_lockout_minutes) * (2**level), MAX_LOCKOUT)
        user.locked_until = _now() + duration
        security_log.security_event(
            security_log.ACCOUNT_LOCKED, user.id, lock_minutes=int(duration.total_seconds() // 60)
        )


def reset_failed_attempts(user: User) -> None:
    """Remet le compteur à zéro après une connexion réussie ou une réinitialisation."""
    user.failed_login_count = 0
    user.locked_until = None


def login(db: Session, *, email: str, password: str) -> AuthSession | MfaChallenge:
    """Vérifie le courriel et le mot de passe, puis selon le compte :
    - MFA activée            → MfaChallenge (il faudra un code TOTP sur /mfa/verify);
    - personnel sans MFA     → session limitée (configuration de la MFA seulement);
    - client                 → session complète (jeton d'accès + jeton de rafraîchissement).
    """
    # Ligne verrouillée : deux tentatives simultanées ne peuvent pas perdre un échec du compteur.
    user = user_repository.get_by_email(db, normalize_email(email), for_update=True)

    if user is not None:
        # Compte bloqué : on ne vérifie même pas le mot de passe, sinon le blocage ne servirait à rien.
        ensure_not_locked(user)

    # Toujours exécuté, même sans compte, pour que le temps de réponse ne trahisse rien.
    password_ok = security.verify_password(password, user.password_hash if user else None)

    if user is None or not password_ok:
        if user is not None:
            register_failed_attempt(user)
            db.commit()
            security_log.security_event(
                security_log.LOGIN_FAILED, user.id, failed_count=user.failed_login_count
            )
        raise Unauthorized(*INVALID_CREDENTIALS)
    if not user.is_active:
        # Même message qu'un mauvais mot de passe : on ne révèle pas qu'un compte est désactivé.
        raise Unauthorized(*INVALID_CREDENTIALS)

    reset_failed_attempts(user)
    user.last_login_at = _now()
    if security.password_needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)

    if user.mfa_enabled:
        db.commit()
        return MfaChallenge(mfa_token=security.create_mfa_challenge_token(user.id))

    if user.is_staff:
        # Personnel sans MFA configurée : session limitée de 15 min, sans jeton de rafraîchissement,
        # qui ne donne accès qu'à la configuration de la MFA (vérifié dans deps.py).
        db.commit()
        return AuthSession(
            access_token=security.create_access_token(user.id, mfa=False),
            expires_in=get_settings().access_token_expire_minutes * 60,
            refresh_token=None,
            mfa_setup_required=True,
        )

    session = open_session(db, user, mfa_verified=False)
    db.commit()
    return session


# ---------------------------------------------------------------------------
# Réinitialisation du mot de passe (A-AUTH-04)
# ---------------------------------------------------------------------------
def forgot_password(db: Session, schedule: Scheduler, email: str) -> None:
    """Toujours la même réponse, que le courriel existe ou non (aucune énumération)."""
    user = user_repository.get_by_email(db, normalize_email(email))
    if user is None or not user.is_active:
        return
    token = _create_one_time_token(
        db,
        user,
        OneTimeTokenPurpose.PASSWORD_RESET,
        timedelta(minutes=get_settings().password_reset_expire_minutes),
    )
    db.commit()
    security_log.security_event(security_log.PASSWORD_RESET_REQUESTED, user.id)
    schedule(email_service.send_password_reset_email, user.email, user.language, token)


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    """Change le mot de passe avec le jeton reçu par courriel (usage unique, 30 min), puis
    ferme toutes les sessions et invalide les jetons d'accès déjà émis."""
    stored = token_repository.get_one_time_token_for_update(
        db, security.hash_token(token), OneTimeTokenPurpose.PASSWORD_RESET
    )
    now = _now()
    if stored is None or stored.used_at is not None or stored.expires_at <= now:
        raise AppError("invalid_or_expired_token", "Ce lien est invalide ou a expiré.")
    user = user_repository.lock_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        raise AppError("invalid_or_expired_token", "Ce lien est invalide ou a expiré.")

    # Vérifié avant de consommer le jeton : l'utilisateur peut réessayer avec un meilleur mot de passe.
    validate_password(new_password, email=user.email, first_name=user.first_name, last_name=user.last_name)

    stored.used_at = now
    user.password_hash = security.hash_password(new_password)
    reset_failed_attempts(user)
    if user.email_verified_at is None:
        user.email_verified_at = now  # le lien reçu prouve que la personne contrôle ce courriel
    # Déconnecte toutes les sessions : si le compte était compromis, l'intrus perd l'accès,
    # y compris avec un jeton d'accès encore valide (refusé par deps.py grâce à tokens_valid_after).
    token_repository.revoke_all_refresh_tokens(db, user.id, now)
    user.tokens_valid_after = now
    db.commit()
    security_log.security_event(security_log.PASSWORD_RESET_COMPLETED, user.id)


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    """Utilisé par deps.py pour relire l'utilisateur (et son rôle) à chaque requête."""
    return user_repository.get_by_id(db, user_id)
