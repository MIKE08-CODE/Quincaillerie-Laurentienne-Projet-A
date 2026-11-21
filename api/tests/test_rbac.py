"""A-AUTH-05 — Contrôle d'accès basé sur les rôles + affectation du personnel à un magasin.
CA : tests automatisés pour chaque rôle sur chaque point de terminaison protégé.

La matrice ci-dessous DOIT grandir avec le projet : chaque nouvelle route protégée (commandes,
stocks, administration…) y ajoute sa ligne, avec le code attendu pour chacun des 5 rôles.
"""

import pytest

from app.models import UserRole
from tests.conftest import auth_header

VISITOR = "visitor"
ROLES = [VISITOR, UserRole.CLIENT, UserRole.CLERK, UserRole.MANAGER, UserRole.ADMIN]

# route → code attendu pour : visiteur, client, commis, gérant, administrateur
MATRIX = {
    "/api/v1/auth/me": (401, 200, 200, 200, 200),
    "/test/any": (401, 200, 200, 200, 200),
    "/test/staff": (401, 403, 200, 200, 200),
    "/test/manager": (401, 403, 403, 200, 200),
    "/test/admin": (401, 403, 403, 403, 200),
    "/test/orders": (401, 200, 200, 200, 200),
    "/test/stores/{own_store}": (401, 403, 200, 200, 200),
    "/test/stores/{other_store}": (401, 403, 403, 403, 200),
}


@pytest.fixture
def stores(make_store):
    return {"own_store": make_store("Magasin Laval"), "other_store": make_store("Magasin Québec")}


@pytest.mark.parametrize("route", MATRIX)
@pytest.mark.parametrize("role_index", range(len(ROLES)), ids=[str(r) for r in ROLES])
def test_role_matrix(client, make_user, stores, route, role_index):
    role = ROLES[role_index]
    path = route.format(**{name: store.id for name, store in stores.items()})

    headers = {}
    if role != VISITOR:
        # Le personnel est affecté au premier magasin seulement.
        assigned = [stores["own_store"]] if role in (UserRole.CLERK, UserRole.MANAGER) else []
        headers = auth_header(make_user(role, stores=assigned), mfa=True)

    response = client.get(path, headers=headers)
    assert response.status_code == MATRIX[route][role_index], response.text


def test_role_change_applies_immediately(client, db, make_user):
    """Le rôle est relu en base à chaque requête : un jeton existant ne garde pas l'ancien rôle."""
    user = make_user(UserRole.ADMIN)
    headers = auth_header(user)
    assert client.get("/test/admin", headers=headers).status_code == 200

    user.role = UserRole.CLIENT
    db.commit()
    assert client.get("/test/admin", headers=headers).status_code == 403


def test_deactivated_account_loses_access_immediately(client, db, make_user):
    user = make_user()
    headers = auth_header(user)
    user.is_active = False
    db.commit()
    assert client.get("/test/any", headers=headers).status_code == 401
