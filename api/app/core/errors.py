"""Erreurs métier.

Les services lèvent ces erreurs sans rien savoir de HTTP (ENF-11 : architecture en couches);
le gestionnaire branché dans main.py les transforme en réponse JSON :

    {"detail": {"code": "password_too_short", "message": "..."}}

Le `code` est stable : les applications web et mobile s'en servent pour afficher le message
traduit en FR ou en EN (ENF-10). Le `message` français sert de valeur par défaut.
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, code: str, message: str, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.headers = headers


class ValidationFailed(AppError):
    status_code = 422


class Unauthorized(AppError):
    status_code = 401

    def __init__(self, code: str = "not_authenticated", message: str = "Authentification requise.") -> None:
        super().__init__(code, message, headers={"WWW-Authenticate": "Bearer"})


class Forbidden(AppError):
    status_code = 403


class AccountLocked(AppError):
    status_code = 423


class Conflict(AppError):
    status_code = 409


class PayloadTooLarge(AppError):
    status_code = 413


class UnsupportedMediaType(AppError):
    status_code = 415


class ServiceUnavailable(AppError):
    """Dépendance externe absente ou non configurée (p. ex. stockage des images)."""

    status_code = 503


class NotFound(AppError):
    """Ressource inexistante, ou invisible pour cet utilisateur (produit désactivé, par exemple)."""

    status_code = 404
