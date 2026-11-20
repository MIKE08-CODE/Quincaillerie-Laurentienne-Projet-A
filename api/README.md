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
| `alembic/versions/` | Migrations de schéma |
| `tests/` | Tests |
