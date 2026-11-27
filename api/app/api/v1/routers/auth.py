"""Routes /api/v1/auth/* (cahier, module A.4.1).

Aucune logique métier ici (ENF-11) : on lit la requête, on appelle le service, on pose ou on
efface le cookie, on renvoie la réponse. Les règles sont dans app/services/auth_service.py et
app/services/mfa_service.py.

Les docstrings des routes sont affichées dans Swagger (/docs) : elles s'adressent aux développeurs
du web, du mobile et du bureau qui consomment l'API.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_user, get_principal
from app.core import rate_limit
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    EmailRequest,
    ErrorResponse,
    LoginRequest,
    MessageResponse,
    MfaChallengeResponse,
    MfaCodeRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    ProfileUpdate,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service, mfa_service, profile_service

router = APIRouter(prefix="/auth", tags=["authentification"])

REFRESH_COOKIE = "ql_refresh"
# Le cookie n'est envoyé qu'aux routes d'authentification, jamais au reste de l'API.
REFRESH_COOKIE_PATH = "/api/v1/auth"

# Messages identiques que le compte existe ou non (aucune énumération d'utilisateurs).
REGISTER_ACCEPTED = "Si l'inscription est valide, un courriel de confirmation vous a été envoyé."
EMAIL_SENT = "Si un compte correspond à ce courriel, un message vous a été envoyé."


# ---------------------------------------------------------------------------
# Réponses d'erreur documentées dans Swagger
# ---------------------------------------------------------------------------
def _error(description: str) -> dict:
    return {"model": ErrorResponse, "description": description}


ERR_422 = {422: _error("Données invalides ou mot de passe trop faible (`password_too_short`, …).")}
ERR_429 = {429: _error("Trop de requêtes depuis cette adresse IP (`rate_limited`). Voir `Retry-After`.")}
ERR_401_TOKEN = {401: _error("Jeton absent, expiré ou invalide (`not_authenticated`, `invalid_token`).")}


# ---------------------------------------------------------------------------
# Cookie du jeton de rafraîchissement (A-AUTH-02)
# ---------------------------------------------------------------------------
def _set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    """Témoin httpOnly (illisible par JavaScript), Secure (HTTPS seulement), SameSite (A-AUTH-02)."""
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,  # les navigateurs l'acceptent aussi sur http://localhost
        samesite=get_settings().refresh_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=get_settings().refresh_cookie_samesite,
    )


def _token_response(response: Response, session: auth_service.AuthSession) -> TokenResponse:
    if session.refresh_token:
        _set_refresh_cookie(response, session.refresh_token, session.refresh_expires_in)
    return TokenResponse(
        access_token=session.access_token,
        expires_in=session.expires_in,
        mfa_setup_required=session.mfa_setup_required,
    )


# ---------------------------------------------------------------------------
# Inscription et vérification du courriel (A-AUTH-01)
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Créer un compte client",
    responses={**ERR_422, **ERR_429},
)
@limiter.limit(rate_limit.REGISTER_LIMIT)
def register(
    request: Request, body: RegisterRequest, background: BackgroundTasks, db: Session = Depends(get_db)
) -> MessageResponse:
    """Crée un compte **client** et envoie un courriel avec un lien de confirmation (valide 24 h).

    - Le consentement à la politique de confidentialité est **obligatoire** (`accept_privacy_policy: true`);
      sa date et sa version sont enregistrées (Loi 25).
    - Le mot de passe doit faire au moins 12 caractères et ne pas être un mot de passe courant.
    - Le rôle ne peut pas être choisi : les comptes du personnel sont créés par un administrateur.
    - **La réponse est la même si le courriel est déjà utilisé** (pour ne pas révéler quels comptes
      existent); le propriétaire du compte est alors prévenu par courriel.
    - Tant que le courriel n'est pas confirmé, le client peut se connecter mais **pas commander**.

    Limite : 5 requêtes par minute par adresse IP.
    """
    auth_service.register(
        db,
        background.add_task,
        email=body.email,
        password=body.password.get_secret_value(),
        first_name=body.first_name,
        last_name=body.last_name,
        language=body.language,
        marketing_opt_in=body.marketing_opt_in,
    )
    return MessageResponse(message=REGISTER_ACCEPTED)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Confirmer le courriel",
    responses={400: _error("Lien invalide, déjà utilisé ou expiré (`invalid_or_expired_token`)."), **ERR_429},
)
@limiter.limit(rate_limit.TOKEN_SUBMIT_LIMIT)
def verify_email(request: Request, body: TokenRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """Confirme le courriel avec le jeton du lien reçu (`…/verifier-courriel#token=XYZ`).

    Le jeton est **à usage unique** : un deuxième appel avec le même jeton renvoie 400.
    En développement, le lien s'affiche dans le terminal du serveur.
    """
    auth_service.verify_email(db, body.token)
    return MessageResponse(message="Votre courriel est confirmé.")


@router.post(
    "/verify-email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Renvoyer le courriel de confirmation",
    responses={**ERR_422, **ERR_429},
)
@limiter.limit(rate_limit.PASSWORD_FORGOT_LIMIT)
def resend_verification(
    request: Request, body: EmailRequest, background: BackgroundTasks, db: Session = Depends(get_db)
) -> MessageResponse:
    """Envoie un nouveau lien de confirmation; l'ancien lien cesse de fonctionner.

    **Même réponse que le compte existe ou non.** Limite : 5 requêtes par minute par adresse IP.
    """
    auth_service.resend_verification(db, background.add_task, body.email)
    return MessageResponse(message=EMAIL_SENT)


# ---------------------------------------------------------------------------
# Connexion, rafraîchissement, déconnexion (A-AUTH-02, A-AUTH-07)
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse | MfaChallengeResponse,
    summary="Se connecter",
    responses={
        200: {
            "description": "Connexion réussie (`TokenResponse` + cookie `ql_refresh`) **ou** code MFA "
            "requis (`MfaChallengeResponse`, sans cookie)."
        },
        401: _error(
            "Courriel ou mot de passe invalide (`invalid_credentials`) — même message dans les deux cas."
        ),
        423: _error(
            "Compte bloqué après 5 échecs (`account_locked`). Voir l'en-tête `Retry-After` (secondes)."
        ),
        **ERR_422,
        **ERR_429,
    },
)
@limiter.limit(rate_limit.LOGIN_LIMIT)
def login(
    request: Request, response: Response, body: LoginRequest, db: Session = Depends(get_db)
) -> TokenResponse | MfaChallengeResponse:
    """Vérifie le courriel et le mot de passe. Trois réponses possibles :

    - **Client** : `access_token` (15 min) + cookie httpOnly `ql_refresh` (7 jours).
    - **Personnel sans MFA configurée** : `access_token` avec `mfa_setup_required: true` et **sans
      cookie**. Ce jeton ne sert qu'à `/mfa/setup` puis `/mfa/enable`.
    - **Compte avec MFA** : `mfa_required: true` + `mfa_token`, à envoyer à `/mfa/verify` avec le code.

    **Verrouillage progressif** : après 5 échecs, le compte est bloqué 15 minutes (423), puis 30, puis 60…
    Pendant le blocage, même le bon mot de passe est refusé.
    Limite : 10 requêtes par minute par adresse IP.
    """
    result = auth_service.login(db, email=body.email, password=body.password.get_secret_value())
    if isinstance(result, auth_service.MfaChallenge):
        return MfaChallengeResponse(mfa_token=result.mfa_token)
    return _token_response(response, result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Obtenir un nouveau jeton d'accès",
    responses={
        401: _error("Cookie absent, expiré ou révoqué (`invalid_refresh_token`) : il faut se reconnecter."),
        **ERR_429,
    },
)
@limiter.limit(rate_limit.REFRESH_LIMIT)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    """Échange le cookie `ql_refresh` contre un nouveau jeton d'accès. **Aucun corps à envoyer** :
    le navigateur joint le cookie automatiquement (côté web : `fetch(..., {credentials: "include"})`).

    - **Rotation** : chaque appel remplace le cookie par un nouveau; l'ancien devient inutilisable.
    - Si un ancien cookie est présenté de nouveau (signe de vol), **toutes les sessions** de
      l'utilisateur sont fermées.
    - Une session dure au plus 30 jours, même si elle est rafraîchie régulièrement.
    """
    session = auth_service.refresh_session(db, request.cookies.get(REFRESH_COOKIE))
    return _token_response(response, session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Se déconnecter")
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    """Révoque le jeton de rafraîchissement (cookie `ql_refresh`) et efface le cookie.

    Réussit toujours (204), même sans cookie. Le client doit aussi oublier son jeton d'accès,
    qui reste techniquement valide jusqu'à son expiration (15 min au plus).
    """
    auth_service.logout(db, request.cookies.get(REFRESH_COOKIE))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil de l'utilisateur connecté",
    responses={**ERR_401_TOKEN, 403: _error("Personnel sans MFA complétée (`mfa_required`).")},
)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    """Renvoie le profil et le rôle de l'utilisateur. Nécessite un jeton d'accès (**Authorize** 🔒).

    `marketing_opt_in` indique si le client accepte les courriels promotionnels (A-PRV-01).
    """
    return _profile_response(db, user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Modifier son profil",
    responses={
        **ERR_401_TOKEN,
        403: _error("Personnel sans MFA complétée (`mfa_required`)."),
        422: _error("Champ inconnu (p. ex. `email`, `role`), valeur `null` ou valeur invalide."),
    },
)
def update_me(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserResponse:
    """Modifie le nom, la langue ou la préférence de communication (A-PRV-01). **Modification
    partielle** : seuls les champs envoyés sont changés, p. ex. `{"language": "en"}`.

    - Le **courriel**, le **rôle** et le **mot de passe** ne sont pas modifiables ici (422).
    - `marketing_opt_in: true` enregistre un consentement daté; `false` le retire. L'historique des
      consentements est conservé (Loi 25).
    - Renvoie le profil à jour, comme `GET /auth/me`.
    """
    # Le schéma a déjà refusé les champs interdits; `exclude_unset` ne garde que ceux envoyés.
    updated = profile_service.update_profile(db, user, body.model_dump(exclude_unset=True))
    return _profile_response(db, updated)


def _profile_response(db: Session, user: User) -> UserResponse:
    """Profil public de l'utilisateur, avec la préférence marketing lue dans `consents`."""
    return UserResponse.model_validate(user).model_copy(
        update={"marketing_opt_in": profile_service.marketing_opt_in(db, user)}
    )


# ---------------------------------------------------------------------------
# Réinitialisation du mot de passe (A-AUTH-04)
# ---------------------------------------------------------------------------
@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Demander un lien de réinitialisation",
    responses={**ERR_422, **ERR_429},
)
@limiter.limit(rate_limit.PASSWORD_FORGOT_LIMIT)
def forgot_password(
    request: Request, body: EmailRequest, background: BackgroundTasks, db: Session = Depends(get_db)
) -> MessageResponse:
    """Envoie un lien de réinitialisation **valide 30 minutes et utilisable une seule fois**.
    Une nouvelle demande annule le lien précédent.

    **La réponse est identique que le courriel existe ou non** : on ne peut pas s'en servir pour
    savoir qui a un compte. Limite : 5 requêtes par minute par adresse IP.
    """
    auth_service.forgot_password(db, background.add_task, body.email)
    return MessageResponse(message=EMAIL_SENT)


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    summary="Choisir un nouveau mot de passe",
    responses={
        400: _error("Lien invalide, déjà utilisé ou expiré (`invalid_or_expired_token`)."),
        **ERR_422,
        **ERR_429,
    },
)
@limiter.limit(rate_limit.TOKEN_SUBMIT_LIMIT)
def reset_password(
    request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    """Change le mot de passe avec le jeton du lien reçu (`…/reinitialiser-mot-de-passe#token=XYZ`).

    - Si le nouveau mot de passe est trop faible (422), le lien reste utilisable pour réessayer.
    - En cas de succès, **toutes les sessions sont fermées** (appareils et jetons d'accès déjà émis) :
      il faut se reconnecter. Le blocage éventuel du compte est levé.
    """
    auth_service.reset_password(db, token=body.token, new_password=body.new_password.get_secret_value())
    return MessageResponse(message="Votre mot de passe a été modifié. Veuillez vous reconnecter.")


# ---------------------------------------------------------------------------
# MFA TOTP (A-AUTH-06)
# ---------------------------------------------------------------------------
@router.post(
    "/mfa/setup",
    response_model=MfaSetupResponse,
    summary="MFA, étape 1 : générer le code QR",
    responses={
        **ERR_401_TOKEN,
        409: _error("La MFA est déjà activée (`mfa_already_enabled`)."),
        **ERR_429,
    },
)
@limiter.limit(rate_limit.TOKEN_SUBMIT_LIMIT)
def mfa_setup(
    request: Request, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> MfaSetupResponse:
    """Génère un secret TOTP et l'adresse `otpauth://` à afficher en **code QR**.

    Accepte le jeton limité reçu à la connexion (`mfa_setup_required: true`). La MFA n'est pas
    encore active : il faut confirmer avec un premier code sur `/mfa/enable`.
    """
    result = mfa_service.setup(db, principal.user)
    return MfaSetupResponse(secret=result.secret, otpauth_uri=result.otpauth_uri)


@router.post(
    "/mfa/enable",
    response_model=TokenResponse,
    summary="MFA, étape 2 : activer avec un premier code",
    responses={
        401: _error("Code invalide (`invalid_mfa_code`) ou jeton absent/expiré."),
        400: _error("`/mfa/setup` n'a pas encore été appelé (`mfa_setup_required`)."),
        409: _error("La MFA est déjà activée (`mfa_already_enabled`)."),
        423: _error("Compte bloqué après 5 codes erronés (`account_locked`)."),
        **ERR_422,
        **ERR_429,
    },
)
@limiter.limit(rate_limit.TOKEN_SUBMIT_LIMIT)
def mfa_enable(
    request: Request,
    response: Response,
    body: MfaCodeRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Vérifie le premier code de l'application d'authentification et active la MFA.
    Renvoie une **session complète** (jeton d'accès + cookie) : le personnel a maintenant accès à ses routes.

    Les codes erronés comptent dans le verrouillage du compte (5 échecs → blocage).
    """
    return _token_response(response, mfa_service.enable(db, principal.user, body.code))


@router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    summary="Se connecter, étape 2 : saisir le code MFA",
    responses={
        401: _error("Code invalide (`invalid_mfa_code`) ou `mfa_token` expiré (`invalid_mfa_token`)."),
        423: _error("Compte bloqué après 5 codes erronés (`account_locked`)."),
        **ERR_422,
        **ERR_429,
    },
)
@limiter.limit(rate_limit.TOKEN_SUBMIT_LIMIT)
def mfa_verify(
    request: Request, response: Response, body: MfaVerifyRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """Deuxième étape de la connexion d'un compte avec MFA : envoie le `mfa_token` reçu de `/login`
    (valide 5 minutes) et le code à 6 chiffres. Renvoie une session complète.

    Un même code ne peut servir qu'**une seule fois**. Les codes erronés comptent dans le verrouillage.
    """
    return _token_response(response, mfa_service.verify_challenge(db, body.mfa_token, body.code))
