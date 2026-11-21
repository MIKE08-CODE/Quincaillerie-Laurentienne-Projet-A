# api — Backend

API REST de Quincaillerie Laurentienne.

**Stack prévue :** FastAPI, SQLAlchemy, Alembic, PostgreSQL.

| Dossier | Rôle |
|---|---|
| `app/api/v1/routers/` | Routes HTTP versionnées (v1) |
| `app/core/` | Configuration, sécurité, paramètres |
| `app/models/` | Modèles ORM SQLAlchemy |
| `app/schemas/` | Schémas Pydantic (entrées/sorties) |
| `app/services/` | Logique métier |
| `app/repositories/` | Accès aux données |
| `app/db/` | Session, moteur, base déclarative |
| `app/seed/` | Données d'amorçage du L1 (`python -m app.seed.seed_l1`) |
| `alembic/versions/` | Migrations de schéma |
| `tests/` | Tests |

## Lancer l'API en local

Prérequis : Python 3.11+, PostgreSQL 16, et un fichier `.env` à la racine du dépôt.

```bash
# 1. Configuration (depuis la racine du dépôt)
cp .env.example .env
#    puis remplir SECRET_KEY, DATABASE_URL et MFA_ENCRYPTION_KEY :
python -c "import secrets; print(secrets.token_urlsafe(48))"                                 # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"    # MFA_ENCRYPTION_KEY

# 2. Environnement Python (depuis api/)
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 3. Base de données (PostgreSQL 16 ; l'extension unaccent est créée par la migration)
alembic upgrade head
python -m app.seed.seed_l1          # données de démonstration L1 (idempotent : relançable)

# 4. Serveur
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs · Santé : http://localhost:8000/health

En développement, les courriels (vérification, réinitialisation) ne sont pas envoyés : ils
s'affichent dans le terminal du serveur, avec le lien à ouvrir.

## Tests

Les tests utilisent une vraie base PostgreSQL, séparée de celle de développement (port 5433) :

```bash
docker run -d --name ql-test-db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=quincaillerie_test -p 127.0.0.1:5433:5432 postgres:16-alpine

pytest --cov                        # tous les tests + couverture
pytest tests/test_lockout.py -v     # démonstration du verrouillage (A-AUTH-07)
ruff check . && ruff format --check .
```

## Authentification (module A.4.1)

Toutes les routes sont sous `/api/v1/auth`.

| Route | Accès | Exigence |
|---|---|---|
| `POST /register` | Public | A-AUTH-01, 03 |
| `POST /verify-email`, `POST /verify-email/resend` | Public | A-AUTH-01 |
| `POST /login` | Public | A-AUTH-02, 07 |
| `POST /refresh` (cookie) · `POST /logout` | Public (cookie) | A-AUTH-02 |
| `GET /me` | Authentifié | — |
| `POST /password/forgot`, `POST /password/reset` | Public | A-AUTH-04 |
| `POST /mfa/setup`, `POST /mfa/enable` | Authentifié (MFA en cours) | A-AUTH-06 |
| `POST /mfa/verify` | Jeton de défi MFA | A-AUTH-06 |

Les erreurs ont toujours la forme `{"detail": {"code": "...", "message": "..."}}`. Le web et le
mobile traduisent le `code` en FR/EN.

## Catalogue (A-CAT-01 à 03, A-ADM-01)

Détails : [`docs/architecture/catalogue-l1.md`](../docs/architecture/catalogue-l1.md).

| Route | Accès | Exigence |
|---|---|---|
| `GET /api/v1/categories` · `GET /api/v1/stores` | Public | A-CAT-01, A-CAT-02 |
| `GET /api/v1/products` (`page`, `size` ≤ 50, `sort`, `category_id`, `brand_id`) | Public | A-CAT-01 |
| `GET /api/v1/products/{id}` · `GET /api/v1/products/{id}/availability` | Public | A-CAT-02 |
| `GET /api/v1/search?q=` (FR/EN, sans accents) | Public | A-CAT-03 |
| `/api/v1/admin/products`, `/admin/categories`, `/admin/brands` (PATCH, désactivation) | Administrateur + MFA | A-ADM-01 |

Démonstration rapide, une fois l'API lancée et la base amorcée :

```bash
curl "http://localhost:8000/api/v1/products?size=5&sort=price_asc"
curl "http://localhost:8000/api/v1/search?q=equerre"
curl "http://localhost:8000/api/v1/search?q=drill"
```

**Protéger une nouvelle route** : utiliser les dépendances de `app/api/deps.py`
(`get_current_user`, `require_roles(...)`, `require_store_access`, `require_verified_email`), puis
ajouter la route à la matrice de `tests/test_rbac.py` avec le code attendu pour chacun des 5 rôles.
