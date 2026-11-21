"""Registre des modèles SQLAlchemy.

Chaque nouveau modèle doit être importé ici : alembic/env.py importe ce paquet, et Alembic
ne détecte que les tables dont le modèle a été importé.
"""

from app.models.auth_token import OneTimeToken, OneTimeTokenPurpose, RefreshToken
from app.models.consent import Consent, ConsentType
from app.models.store import StaffAssignment, Store
from app.models.user import STAFF_ROLES, User, UserRole

__all__ = [
    "STAFF_ROLES",
    "Consent",
    "ConsentType",
    "OneTimeToken",
    "OneTimeTokenPurpose",
    "RefreshToken",
    "StaffAssignment",
    "Store",
    "User",
    "UserRole",
]
