"""Dépendances d'authentification et d'autorisation, utilisées par TOUS les routeurs.

Visiteur          → aucune dépendance (route publique)
Tout utilisateur  → Depends(get_current_user)
Rôles précis      → Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN))
Magasin précis    → Depends(require_store_access)  (lit `store_id` dans le chemin)
Commande          → Depends(require_verified_email)  (A-AUTH-01)

Le rôle n'est pas lu dans le jeton mais en base, à chaque requête (ENF-04 : décision côté serveur).
Ces dépendances vérifient le RÔLE; la PROPRIÉTÉ (« cette commande est-elle à lui? ») reste à
vérifier dans chaque service, avec l'utilisateur fourni ici.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.errors import Forbidden, Unauthorized
from app.db.session import get_db
from app.models import User, UserRole
from app.services import auth_service

# auto_error=False : on lève nous-mêmes une erreur 401 au format habituel de l'API.
_bearer = HTTPBearer(
    auto_error=False,
    description="Jeton d'accès reçu de `/api/v1/auth/login` (coller la valeur seule, sans « Bearer »).",
)


@dataclass(frozen=True)
class Principal:
    """Utilisateur authentifié + indique si la session a complété la MFA."""

    user: User
    mfa_verified: bool


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    """Utilisateur authentifié, MFA complétée ou non. À réserver aux routes de configuration MFA."""
    if credentials is None:
        raise Unauthorized()
    try:
        payload = security.decode_jwt(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (security.InvalidTokenError, ValueError):
        # Jeton expiré, falsifié ou mal formé → 401 (CA d'A-AUTH-02).
        raise Unauthorized("invalid_token", "Jeton invalide ou expiré.") from None

    user = auth_service.get_user(db, user_id)
    if user is None or not user.is_active or security.issued_before(payload, user.tokens_valid_after):
        # Compte supprimé ou désactivé, ou jeton émis avant une réinitialisation du mot de passe.
        raise Unauthorized("invalid_token", "Jeton invalide ou expiré.")
    return Principal(user=user, mfa_verified=bool(payload.get("mfa", False)))


def get_current_user(principal: Principal = Depends(get_principal)) -> User:
    """Utilisateur authentifié. Le personnel doit avoir complété la MFA (CA d'A-AUTH-06)."""
    if principal.user.is_staff and not principal.mfa_verified:
        raise Forbidden("mfa_required", "L'authentification multifacteur est requise pour le personnel.")
    return principal.user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Fabrique une dépendance qui n'accepte que les rôles donnés (A-AUTH-05)."""
    allowed = frozenset(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise Forbidden("insufficient_role", "Vous n'avez pas les droits nécessaires.")
        return user

    return dependency


def require_verified_email(user: User = Depends(get_current_user)) -> User:
    """À utiliser sur le paiement d'une commande : un compte non vérifié ne peut pas commander."""
    if not user.is_email_verified:
        raise Forbidden("email_not_verified", "Veuillez d'abord confirmer votre courriel.")
    return user


def ensure_store_access(user: User, store_id: uuid.UUID) -> None:
    """Le commis et le gérant n'agissent que sur LEUR magasin; l'administrateur sur tous."""
    if user.role == UserRole.ADMIN:
        return
    if user.role in (UserRole.CLERK, UserRole.MANAGER) and store_id in user.store_ids:
        return
    raise Forbidden("store_access_denied", "Vous n'avez pas accès à ce magasin.")


def require_store_access(
    store_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN)),
) -> User:
    """Pour les routes du type /stores/{store_id}/... : personnel affecté à ce magasin, ou admin."""
    ensure_store_access(user, store_id)
    return user
