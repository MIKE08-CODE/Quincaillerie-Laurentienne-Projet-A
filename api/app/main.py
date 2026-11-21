"""Point d'entrée de l'API Quincaillerie Laurentienne.

Lancement local (depuis le dossier `api/`) : `uvicorn app.main:app --reload --port 8001`
Documentation interactive : http://localhost:8001/docs

Ce fichier assemble l'application : configuration, middlewares (CORS, en-têtes de sécurité),
format des erreurs, limitation de débit et routeurs. Il ne contient aucune logique métier.
"""

import logging

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.routers import admin_catalog, auth, catalog
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import limiter

API_V1_PREFIX = "/api/v1"

# Texte d'accueil de Swagger (/docs), en Markdown.
API_DESCRIPTION = """
API REST de la Quincaillerie Laurentienne, consommée par l'application web, l'application mobile
et l'application de bureau. **Toutes les décisions de sécurité sont prises ici, par le serveur.**

## Tester une route protégée dans cette page
1. `POST /api/v1/auth/login` → copier la valeur de `access_token`.
2. Cliquer sur **Authorize** 🔒 (en haut à droite) et coller le jeton (sans le mot « Bearer »).
3. Le jeton d'accès expire après **15 minutes** : appeler `POST /api/v1/auth/refresh` pour en obtenir un
   nouveau (le navigateur envoie automatiquement le cookie `ql_refresh`).

## Les deux jetons
| Jeton | Durée | Où il voyage |
|---|---|---|
| Accès (JWT) | 15 min | En-tête `Authorization: Bearer …`, gardé **en mémoire** par le client |
| Rafraîchissement | 7 jours (30 jours max. par session) | Cookie `ql_refresh` httpOnly, Secure, SameSite |

## Format des erreurs
Toutes les erreurs ont la même forme. Le `code` est stable : les applications le traduisent en FR/EN.
```json
{"detail": {"code": "invalid_credentials", "message": "Courriel ou mot de passe invalide."}}
```

## Rôles
`visiteur` (sans jeton) · `client` · `clerk` (commis) · `manager` (gérant) · `admin`.
Le personnel (commis, gérant, administrateur) doit avoir complété la **MFA** pour accéder
aux routes protégées.
"""

TAGS_METADATA = [
    {
        "name": "authentification",
        "description": "Comptes, connexion, jetons, réinitialisation du mot de passe et MFA "
        "(cahier des charges, module A.4.1 : A-AUTH-01 à A-AUTH-07).",
    },
    {
        "name": "catalogue",
        "description": "Catalogue public : catégories, magasins, produits, disponibilité et recherche FR/EN "
        "(A-CAT-01 à A-CAT-03). Aucune authentification.",
    },
    {
        "name": "administration du catalogue",
        "description": "Produits, images, catégories et marques (A-ADM-01). "
        "Rôle administrateur et MFA requis.",
    },
    {"name": "santé", "description": "Surveillance de l'API par l'hébergeur."},
]


def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Transforme les erreurs métier en JSON : {"detail": {"code": ..., "message": ...}}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message}},
        headers=exc.headers,
    )


def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Erreurs de format (422) SANS recopier les valeurs reçues.

    Par défaut, FastAPI renvoie la valeur fautive dans la réponse : un mot de passe trop long serait
    alors renvoyé en clair (et pourrait finir dans les journaux d'un proxy ou du navigateur).
    On ne garde donc que l'emplacement du champ et la raison.
    """
    errors = [
        {"field": ".".join(str(part) for part in error["loc"]), "reason": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "validation_error",
                "message": "Certaines données sont invalides.",
                "errors": errors,
            }
        },
    )


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Limitation de débit dépassée (ENF-05)."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": {"code": "rate_limited", "message": "Trop de requêtes. Réessayez dans un moment."}
        },
        headers={"Retry-After": "60"},
    )


def _configure_logging() -> None:
    """Affiche les journaux de l'application (dont `app.security`) dans le terminal du serveur."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()

    app = FastAPI(
        title="API Quincaillerie Laurentienne",
        version="0.1.0",
        description=API_DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        debug=False,  # jamais de traces d'erreur détaillées envoyées au client (OWASP A05)
    )

    # CORS limité aux origines connues (ENF-03). `allow_credentials` est nécessaire pour que le
    # navigateur envoie le cookie httpOnly du jeton de rafraîchissement (A-AUTH-02).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        """En-têtes de sécurité ajoutés à chaque réponse (ENF-03)."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            # Les réponses de l'API contiennent des jetons et des données personnelles : aucun
            # navigateur ni proxy ne doit les garder en cache. Une route peut l'assouplir
            # (p. ex. le catalogue public) en posant son propre Cache-Control.
            response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            # HSTS seulement en production : en local, on travaille en HTTP.
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/health", tags=["santé"], summary="Vérifier que l'API répond")
    def health() -> dict[str, str]:
        """Point de santé (ENF-13), utilisé par l'hébergeur pour savoir si l'API répond.
        Ne nécessite aucune authentification."""
        return {"status": "ok"}

    app.state.limiter = limiter  # limitation de débit (ENF-05)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)

    # Routeurs des modules, tous sous /api/v1 (cahier A.7).
    app.include_router(auth.router, prefix=API_V1_PREFIX)
    app.include_router(catalog.router, prefix=API_V1_PREFIX)
    app.include_router(admin_catalog.router, prefix=API_V1_PREFIX)

    return app


app = create_app()
