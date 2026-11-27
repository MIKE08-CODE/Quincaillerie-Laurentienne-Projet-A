# ADR-010 — Session des clients natifs (mobile et bureau)

- **Statut :** Proposé (27 novembre 2026) ; **implémenté et testé** (`api/tests/test_native_session.py`) — en attente de l'approbation du responsable.
- **Exigences :** A-AUTH-02 (jetons d'accès courts et rafraîchissement révocable), A-AUTH-06 (MFA du personnel), exigence transversale « Mobile : stockage sécurisé des jetons » ; tranche la décision ouverte **DEC-02** du contrat d'API (§13) et complète l'ADR-002.

## Contexte

Au L1, le jeton de rafraîchissement voyage **uniquement** dans le cookie `ql_refresh` (`HttpOnly`,
`Secure`, `SameSite`, `Path=/api/v1/auth`) : `/auth/login` le pose, `/auth/refresh` et `/auth/logout`
ne le lisent que dans le cookie. Ce choix protège le web : un script injecté ne peut pas lire le jeton.

Les applications natives (React Native + Expo, WPF .NET 8) ne gèrent pas les cookies de façon fiable
ni portable. Sans autre canal, elles ne peuvent pas rafraîchir leur session : l'utilisateur devrait se
reconnecter toutes les 15 minutes (durée du jeton d'accès).

## Options étudiées

| Option | Avantages | Inconvénients | Verdict |
|---|---|---|---|
| Cookies dans le client natif | Aucun changement d'API | Gestion des cookies incomplète selon la plateforme; `Secure`/`SameSite` mal définis hors navigateur | Écartée |
| Jeton d'accès long pour les natifs | Simple | Contraire à A-AUTH-02 (15 min au plus); vol d'un jeton non révocable | Écartée |
| **Jeton de rafraîchissement dans le corps JSON, sur demande explicite du client natif** | Même rotation, même révocation, même détection de vol que le web; aucun changement du service | Le client natif doit stocker le jeton lui-même, dans un stockage sécurisé | **Retenue** |

## Décision

1. **Demande explicite.** `POST /auth/login`, `/auth/mfa/enable` et `/auth/mfa/verify` acceptent
   `"client": "native"` (défaut `"web"`). En mode natif, la réponse contient `refresh_token` et
   `refresh_expires_in`, et **aucun cookie** n'est posé.
2. **Rafraîchissement et déconnexion.** `/auth/refresh` et `/auth/logout` acceptent un corps facultatif
   `{"refresh_token": "…"}`. Un corps présent signifie « client natif » : le nouveau jeton revient dans
   le JSON, sans cookie. Sans corps, le comportement web est inchangé (cookie).
3. **Règle de sécurité : jamais un cookie converti en JSON.** Un jeton reçu par cookie n'est jamais
   recopié dans la réponse. Sinon, un script injecté sur le site appellerait `/auth/refresh` (le
   navigateur joint le cookie tout seul) et lirait le nouveau jeton, annulant la protection `HttpOnly`.
4. **Service inchangé.** `auth_service.refresh_session` et `auth_service.logout` reçoivent déjà le jeton
   brut : rotation à chaque rafraîchissement, fin absolue de session à 30 jours, révocation de toutes
   les sessions si un ancien jeton revient (vol probable), révocation lors d'une réinitialisation du
   mot de passe. Seuls les schémas (`app/schemas/auth.py`) et le routeur (`app/api/v1/routers/auth.py`)
   changent, conformément à la séparation en couches (ENF-11).
5. **Stockage côté client.**
   - Mobile : jeton de rafraîchissement dans `expo-secure-store` (Keychain iOS, Keystore Android),
     jamais dans `AsyncStorage`; jeton d'accès en mémoire seulement.
   - Bureau : stockage protégé par le système (p. ex. DPAPI de Windows), à préciser par l'équipe du bureau.
6. **Personnel sans MFA.** La session limitée (`mfa_setup_required: true`) ne contient jamais de
   jeton de rafraîchissement, en mode web comme en mode natif.
7. **Format de la réponse web inchangé.** Les champs `refresh_token` et `refresh_expires_in` valent
   `null` pour le web et sont retirés du JSON (`response_model_exclude_none`) : la clé n'apparaît pas.

## Conséquences

- Le mobile et le bureau peuvent garder une session jusqu'à 30 jours, avec la même rotation et la même
  détection de vol que le web.
- La sécurité du jeton natif repose sur le stockage sécurisé de l'appareil : c'est une responsabilité
  de chaque client, à vérifier dans ses tests (le jeton ne doit jamais être écrit en clair).
- Aucune protection CSRF supplémentaire n'est nécessaire en mode natif : le jeton n'est pas envoyé
  automatiquement par un navigateur.
- Limite connue : un client qui envoie `"client": "native"` depuis un navigateur reçoit le jeton dans
  le JSON. C'est seulement possible avec le mot de passe (ou le code MFA) en main ; le site web officiel
  n'utilise jamais ce mode.

## Validation

`api/tests/test_native_session.py` (14 tests) : connexion native sans cookie; connexion web inchangée;
valeur de `client` inconnue refusée; rotation dans le corps et ancien jeton refusé; jeton réutilisé
→ toutes les sessions révoquées; rafraîchissement par cookie sans jeton dans le JSON; déconnexion native;
corps invalides refusés (422); réinitialisation du mot de passe qui révoque les sessions natives;
personnel sans MFA sans jeton de rafraîchissement; activation et connexion MFA en mode natif.
