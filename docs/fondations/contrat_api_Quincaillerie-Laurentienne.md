# Contrat d'API — Quincaillerie Laurentienne (Projet A)

|  |  |
| :---- | :---- |
| **Livrable** | L1 — Fondations (cible applicative `v0.1.0`) |
| **Auteur** | \[à compléter\] |
| **Version de l'API** | `v1` |
| **Version documentaire** | `1.3` — 21 novembre 2026 |
| **Statut** | Contrat cible L1 ; conformité au code et déploiement à vérifier |
| **Sources** | Cahier des charges — Projet A (Quincaillerie Laurentienne) : A.7, A.4, A.5, A.6, A.11, section 4 et section 5 (ENF) |

**Portée :** contrat cible de **toute l’API du Projet A (L1, L2 et L3)**, livré documentairement en L1. Le jalon n’indique pas que la route est implémentée. Les champs, méthodes et codes proposés au-delà de la liste indicative A.7 sont des **propositions contractuelles à approuver**.

**Contenu :** 1\. Informations générales · 2\. Sécurité · 3\. En-têtes HTTP · 4\. Pagination, tri et filtres · 5\. Limitation de débit · 6\. Format des erreurs · 7\. Routes contractuelles (L1) · 8\. Schémas et types · 9\. Exemples · 10\. Routes contractuelles cibles (L2 et L3).

**Colonne « Source » :** **CC** \= demandé par le cahier des charges (avec l'exigence). **Proposé** \= valeur choisie par l'équipe, que le cahier des charges ne précise pas; à valider.

FastAPI peut exposer `/docs` (Swagger UI), `/redoc` et `/openapi.json` selon la configuration. **Ce document décrit le contrat visé, et non une preuve de déploiement ou de conformité du code.** La spécification OpenAPI exportée depuis l'API réellement exécutée fera foi pour les endpoints implémentés ; tout écart doit être consigné et résolu avant validation.

---

## 1\. Informations générales

| Sujet | Valeur | Source |
| :---- | :---- | :---- |
| Style d'API | REST, versionnée | CC (section 4\) |
| Préfixe de toutes les routes | `/api/v1` | CC (A.7) |
| Protocole | HTTPS uniquement | CC (ENF-03) |
| Format des données | **JSON** (`application/json; charset=utf-8`). **XML non pris en charge.** | CC (FastAPI \+ Pydantic, section 4.1) |
| Format des envois de fichiers | `multipart/form-data` (images produit, seule exception) | CC (A-ADM-01) |
| Cadre de l'API | FastAPI, Python 3.11+, validation Pydantic | CC (section 4.1) |
| Documentation | `/docs`, `/redoc`, `/openapi.json` | CC (section 4.1) |
| Identifiants | UUID | CC (A.6) |
| Montants | Entiers en cents (`price_cents`), jamais de nombre à virgule flottante | CC (RA-A-04) |
| Dates et heures | ISO 8601, en UTC (ex. `2026-11-20T14:30:00Z`) | Proposé |
| Langues | Champs de texte bilingues `*_fr` et `*_en`; le client choisit | CC (ENF-10, A.6) |
| CORS | Limité aux origines connues | CC (ENF-03) |
| Performance visée | Médiane \< 300 ms en lecture; première réponse de l'agent \< 8 s | CC (ENF-07) |
| Collections | Collections potentiellement volumineuses paginées ; exceptions bornées documentées au §4.2 | CC (ENF-07), modalités proposées |

---

## 2\. Sécurité

### 2.1 Authentification

| Élément | Règle | Source |
| :---- | :---- | :---- |
| Jeton d'accès | JWT, durée de vie de 15 minutes maximum, envoyé dans `Authorization: Bearer <jeton>` | CC (A-AUTH-02) |
| Jeton de rafraîchissement | Cookie `HttpOnly`, `Secure`, `SameSite` pour le Web ; révocation à la déconnexion. Rotation, protection CSRF et stratégie native Mobile/Bureau à vérifier/valider. | CC (A-AUTH-02) + précisions proposées |
| Mot de passe | 12 caractères minimum, vérifié contre une liste de mots de passe courants, haché en Argon2id | CC (A-AUTH-03, ENF-02) |
| Verrouillage | Blocage progressif après des échecs répétés | CC (A-AUTH-07, ENF-05) |
| MFA (TOTP) | Mesure cible pour le personnel et les administrateurs, prévue pour L3 ; non présumée implémentée en L1 | CC (A-AUTH-06) |
| Message d'échec de connexion | Identique que le courriel existe ou non (aucune énumération d'utilisateurs) | CC (A-AUTH-04) |

### 2.2 Autorisation

| Rôle | Accès |
| :---- | :---- |
| Visiteur | Routes publiques : catalogue, recherche, magasins, disponibilité, agent, création de compte |
| Client | Routes publiques \+ panier, commandes, profil, vie privée (ses propres ressources seulement) |
| Commis | Routes `/staff/*` de **son** magasin |
| Gérant | Routes du commis \+ réception, approbation des ajustements, rapports du magasin |
| Administrateur | Routes `/admin/*` |
| Stripe (système) | `POST /webhooks/stripe` seulement, avec signature valide |

| Situation | Réponse | Source |
| :---- | :---- | :---- |
| Jeton absent, invalide ou expiré | 401 | CC (A-AUTH-02) |
| Rôle insuffisant | 403 | CC (ENF-04) |
| Ressource d'un autre utilisateur (IDOR) | 404 | CC (A-D4) |
| Commis d'un autre magasin | 403 ou 404 | CC (A-D4) |

---

## 3\. En-têtes HTTP

### 3.1 En-têtes de requête

| En-tête | Valeur | Obligatoire | Routes | Source |
| :---- | :---- | :---- | :---- | :---- |
| `Authorization` | `Bearer <jeton d'accès>` | Oui | Toutes les routes protégées | CC (A-AUTH-02) |
| `Content-Type` | `application/json` | Oui, si la requête a un corps | `POST`, `PUT` | CC |
| `Content-Type` | `multipart/form-data` | Oui | Téléversement d'images | CC (A-ADM-01) |
| `Accept` | `application/json` | Recommandé | Toutes | CC |
| `Cookie` | `refresh_token=<jeton>` | Oui | `/auth/refresh`, `/auth/logout` | CC (A-AUTH-02) |
| `Stripe-Signature` | Signature du webhook | Oui | `POST /webhooks/stripe` (L2) | CC (A-ORD-05) |

### 3.2 En-têtes de réponse

| En-tête | Valeur | Routes | Source |
| :---- | :---- | :---- | :---- |
| `Content-Type` | `application/json; charset=utf-8` | Toutes (sauf 204\) | CC |
| `Set-Cookie` | `refresh_token=<jeton>; HttpOnly; Secure; SameSite=<valeur à confirmer>; Path=/api/v1/auth` | `/auth/login`, `/auth/refresh` | CC (A-AUTH-02) |
| `X-Request-ID` | Identifiant unique de la requête, le même que dans les journaux | Toutes | Proposé (ENF-13 exige un identifiant de requête dans les journaux) |
| `Retry-After` | Nombre de secondes avant de réessayer | Réponses 429 | Proposé |
| `X-RateLimit-Limit` | Nombre de requêtes autorisées dans la fenêtre | Routes à débit limité | Proposé |
| `X-RateLimit-Remaining` | Requêtes restantes dans la fenêtre | Routes à débit limité | Proposé |
| `X-RateLimit-Reset` | Secondes avant la réinitialisation de la fenêtre | Routes à débit limité | Proposé |
| `Cache-Control` | `no-store` | Réponses d'authentification | Proposé |
| `Strict-Transport-Security` | HSTS | Toutes | CC (ENF-03) |
| `X-Content-Type-Options` | `nosniff` | Toutes | CC (ENF-03) |
| `Referrer-Policy` | Politique de référent | Toutes | CC (ENF-03) |

La `Content-Security-Policy` s'applique à l'application web (ENF-03). Les attributs exacts `SameSite`, `Path` et éventuellement `Domain` du cookie, la rotation/révocation des jetons et la protection CSRF des requêtes authentifiées par cookie restent à confirmer. Sur Mobile et Bureau, prévoir un stockage sécurisé natif des secrets, sans supposer l'usage du cookie navigateur. Les en-têtes listés ici sont contractuels, **pas attestés sur l'API en cours d'exécution**.

---

## 4\. Pagination, tri et filtres

Les collections potentiellement volumineuses sont paginées (A-CAT-01, ENF-07). Les exceptions bornées sont explicitées au §4.2.

### 4.1 Paramètres de requête

| Paramètre | Type | Défaut | Contraintes | Source |
| :---- | :---- | :---- | :---- | :---- |
| `page` | integer | 1 | ≥ 1 | CC (A-CAT-01) |
| `size` | integer | 20 | de 1 à **50** | CC (maximum de 50, A-CAT-01); défaut proposé |
| `sort` | string | `newest` | `price_asc`, `price_desc`, `name_asc`, `name_desc`, `newest` | CC (tri par prix, nom ou nouveauté); valeurs proposées |
| `category_id` | UUID | aucun | catégorie existante | CC (navigation par catégorie) |
| `q` | string | obligatoire sur `/search` | au moins 1 caractère | CC (A-CAT-03) |

Une valeur hors limites (`size=100`, `page=0`) renvoie une erreur **422**.

### 4.2 Corps de réponse paginé

```json
{
  "items": [],
  "page": 1,
  "size": 20,
  "total": 152
}
```

| Champ | Type | Description |
| :---- | :---- | :---- |
| `items` | array | Éléments de la page |
| `page` | integer | Numéro de la page courante |
| `size` | integer | Nombre d'éléments demandés par page |
| `total` | integer | Nombre total d'éléments correspondant à la requête |

Exceptions contractuelles : `GET /categories` (arbre de catégories) et `GET /stores` (magasins) peuvent renvoyer une liste complète non paginée, sous réserve de limites raisonnables et de vérification dans l’OpenAPI réel. Les 3 magasins concernent les données initiales L1, et non une limite permanente du système.

---

## 5\. Limitation de débit

Le cahier des charges exige une limitation sur la connexion, l'inscription, la réinitialisation du mot de passe et l'agent conversationnel (ENF-05), mais ne donne de valeur que pour la connexion. Les autres limites sont proposées et à valider.

| Route | Limite | Clé de comptage | Source |
| :---- | :---- | :---- | :---- |
| `POST /auth/login` (échecs) | 5 échecs consécutifs : blocage de 15 minutes | Compte | CC (exemple de A-AUTH-07) |
| `POST /auth/login` | 10 requêtes par minute | Adresse IP | Proposé |
| `POST /auth/register` | 5 requêtes par heure | Adresse IP | Proposé |
| `POST /auth/verify-email` | 10 requêtes par heure | Adresse IP | Proposé |
| `POST /auth/password/forgot` | 3 requêtes par heure | Adresse IP et courriel | Proposé |
| `POST /auth/password/reset` | 5 requêtes par heure | Adresse IP | Proposé |
| `POST /chat/messages` (L2) | 20 requêtes par minute | Adresse IP | Proposé |
| Autres routes publiques (lecture) | 120 requêtes par minute | Adresse IP | Proposé |
| Routes authentifiées | 300 requêtes par minute | Utilisateur | Proposé |

**Comportement en cas de dépassement :** réponse **429** avec le corps `ErrorOut` (code `rate_limited`) et l'en-tête `Retry-After`. Le webhook Stripe ne doit pas dépendre d’une liste d’IP comme unique contrôle : la signature doit être vérifiée sur le corps brut avant tout traitement métier (A-ORD-05). Des limites de taille, des délais d’attente, une protection contre les abus et l’idempotence restent nécessaires. Les seuils proposés dans ce tableau ne sont **pas réputés actifs** sans vérification de configuration et tests.

---

## 6\. Format des erreurs

### 6.1 Modèle d'erreur général : `ErrorOut` (cible contractuelle)

| Champ | Type | Obligatoire | Description |
| :---- | :---- | :---- | :---- |
| `code` | string | Oui | Code stable lisible par une machine (voir 6.3) |
| `message` | string | Oui | Message lisible; générique pour les erreurs d'authentification |
| `details` | object ou null | Non | Informations additionnelles, sans donnée sensible |
| `request_id` | string | Oui | Identifiant de la requête, le même que `X-Request-ID` |

### 6.2 Erreur de validation : `ValidationErrorOut` (422, cible contractuelle)

| Champ | Type | Obligatoire | Description |
| :---- | :---- | :---- | :---- |
| `code` | string | Oui | Toujours `validation_error` |
| `message` | string | Oui | Message général |
| `errors` | array de `FieldError` | Oui | Une entrée par champ invalide |
| `request_id` | string | Oui | Identifiant de la requête |

`FieldError` : `field` (string, ex. `body.email`), `message` (string), `type` (string, ex. `value_error`). **Attention :** FastAPI/Pydantic renvoie par défaut les erreurs 422 dans `detail`. Le format `ValidationErrorOut` exige un traitement personnalisé ; sa présence doit être vérifiée dans le code et dans `/openapi.json`.

### 6.3 Codes HTTP et codes d'erreur

| HTTP | `code` | Signification | Exemple dans le projet |
| :---- | :---- | :---- | :---- |
| 200 |  | Succès avec corps | `GET /products` |
| 201 |  | Ressource créée | `POST /auth/register`, `POST /admin/products` |
| 202 |  | Demande acceptée | `POST /auth/password/forgot` |
| 204 |  | Succès sans corps | `POST /auth/logout`, `POST /auth/password/reset` |
| 400 | `bad_request` | Requête invalide ou jeton à usage unique invalide | Jeton de réinitialisation déjà utilisé |
| 401 | `unauthorized` | Authentification absente ou invalide | Jeton expiré ou révoqué |
| 403 | `forbidden` | Rôle insuffisant | Client sur une route `/admin/*` |
| 404 | `not_found` | Ressource inexistante ou d'un autre utilisateur | `GET /products/{id}` inconnu |
| 409 | `conflict` | Conflit avec l'état actuel | SKU ou courriel déjà utilisé |
| 413 | `payload_too_large` | Fichier trop volumineux | Image trop grande |
| 415 | `unsupported_media_type` | Type de fichier refusé | Fichier non image |
| 422 | `validation_error` | Données invalides | Mot de passe de moins de 12 caractères |
| 429 | `rate_limited` | Trop de requêtes | Trop d'échecs de connexion |
| 500 | `internal_error` | Erreur interne; message générique, jamais de trace d'exécution |  |

Les erreurs d'authentification ont un message identique, que le courriel existe ou non (A-AUTH-04, ENF-01).

---

## 7\. Routes contractuelles (L1)

Portée de L1 d’après A.11 : A-AUTH-01 à 05 et 07, A-CAT-01 à 03, A-ADM-01, données d’amorçage. **Les tableaux ci-dessous sont des engagements documentaires, pas un inventaire vérifié des routes en production.** Les méthodes, chemins et schémas devront être comparés à l’OpenAPI généré.

### 7.1 Authentification

| Route | Accès | Exigences | Requête | Succès | Erreurs |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `POST /auth/register` | Public | A-AUTH-01, A-AUTH-03 | `RegisterIn` | 201 `UserOut` | 409, 422, 429 |
| `POST /auth/login` | Public | A-AUTH-02, A-AUTH-07 | `LoginIn` | 200 `TokenOut` \+ cookie de rafraîchissement | 401, 422, 429 |
| `POST /auth/refresh` | Cookie de rafraîchissement | A-AUTH-02 | (cookie) | 200 `TokenOut` \+ nouveau cookie | 401 |
| `POST /auth/logout` | Connecté | A-AUTH-02 | (aucune) | 204, jeton de rafraîchissement révoqué | 401 |
| `POST /auth/password/forgot` | Public | A-AUTH-04 | `ForgotPasswordIn` | 202, même réponse que le courriel existe ou non | 422, 429 |
| `POST /auth/password/reset` | Public | A-AUTH-03, A-AUTH-04 | `ResetPasswordIn` | 204 | 400, 422, 429 |

### 7.2 Catalogue et recherche

| Route | Accès | Exigences | Requête | Succès | Erreurs |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `GET /products` | Public | A-CAT-01 | `page`, `size`, `sort`, `category_id` | 200 `Page[ProductSummary]` | 422, 429 |
| `GET /products/{id}` | Public | A-CAT-02 | (aucune) | 200 `ProductDetail` | 404, 422, 429 |
| `GET /products/{id}/availability` | Public | A-CAT-02 | (aucune) | 200 liste de `StoreAvailability` | 404, 422, 429 |
| `GET /categories` | Public | A-CAT-01 | (aucune) | 200 liste de `CategoryNode` | 429 |
| `GET /search` | Public | A-CAT-03 | `q`, `page`, `size` | 200 `Page[ProductSummary]` | 422, 429 |
| `GET /stores` | Public | A-CAT-02 | (aucune) | 200 liste de `StoreOut` | 429 |

### 7.3 Administration des produits

| Route | Accès | Exigences | Requête | Succès | Erreurs |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `GET /admin/products` | Administrateur | A-ADM-01 | `page`, `size` | 200 `Page[ProductAdminOut]` | 401, 403, 422 |
| `POST /admin/products` | Administrateur | A-ADM-01 | `ProductCreate` | 201 `ProductAdminOut` | 401, 403, 409, 422 |
| `GET /admin/products/{id}` | Administrateur | A-ADM-01 | (aucune) | 200 `ProductAdminOut` | 401, 403, 404 |
| `PUT /admin/products/{id}` | Administrateur | A-ADM-01 | `ProductUpdate` | 200 `ProductAdminOut` | 401, 403, 404, 409, 422 |
| `DELETE /admin/products/{id}` | Administrateur | A-ADM-01 | (aucune) | 204, désactive le produit (`is_active`) | 401, 403, 404 |

### 7.4 Santé

| Route | Accès | Exigences | Succès |
| :---- | :---- | :---- | :---- |
| `GET /health` | Public | ENF-13 | 200 `HealthOut` |

### 7.5 Routes complémentaires proposées pour satisfaire une exigence de L1

La liste A.7 est indicative et doit être raffinée par l’équipe. Les opérations suivantes sont proposées pour couvrir des besoins L1 non détaillés dans la liste de routes ; leur implémentation n’est pas attestée :

| Route | Accès | Exigence | Requête | Succès | Erreurs |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `POST /auth/verify-email` | Public | A-AUTH-01 | `VerifyEmailIn` | 204 | 400, 422, 429 |
| `POST /admin/products/{id}/images` | Administrateur | A-ADM-01 | fichier (multipart) | 201 `ImageOut` | 401, 403, 404, 413, 415 |
| `/admin/categories` (CRUD à préciser) | Administrateur | A-ADM-01 | Méthodes, schémas et statuts à définir | À définir | 401, 403, 404, 422 (prévisionnel) |

---

## 8\. Schémas et types

Types JSON : `string`, `integer`, `boolean`, `object`, `array`. Formats : `uuid`, `email`, `date-time`.

### 8.1 Schémas communs

| Schéma | Champ | Type | Obligatoire | Contraintes |
| :---- | :---- | :---- | :---- | :---- |
| `Page[T]` | `items` | array de `T` | Oui |  |
|  | `page` | integer | Oui | ≥ 1 |
|  | `size` | integer | Oui | de 1 à 50 |
|  | `total` | integer | Oui | ≥ 0 |
| `ErrorOut` | `code` | string | Oui |  |
|  | `message` | string | Oui |  |
|  | `details` | object ou null | Non |  |
|  | `request_id` | string | Oui |  |
| `ValidationErrorOut` | `code` | string | Oui | `validation_error` |
|  | `message` | string | Oui |  |
|  | `errors` | array de `FieldError` | Oui |  |
|  | `request_id` | string | Oui |  |
| `FieldError` | `field` | string | Oui |  |
|  | `message` | string | Oui |  |
|  | `type` | string | Oui |  |
| `HealthOut` | `status` | string | Oui | `ok` |

### 8.2 Authentification

| Schéma | Champ | Type | Obligatoire | Contraintes |
| :---- | :---- | :---- | :---- | :---- |
| `RegisterIn` | `email` | string (email) | Oui | courriel valide, unique sans tenir compte de la casse |
|  | `password` | string | Oui | 12 caractères minimum, absent des mots de passe courants |
|  | `first_name` | string | Oui | 1 à 100 caractères |
|  | `last_name` | string | Oui | 1 à 100 caractères |
|  | `language` | string | Non | `fr` (défaut) ou `en` |
|  | `privacy_consent` | boolean | Oui | doit être `true` |
| `UserOut` | `id` | string (uuid) | Oui |  |
|  | `email` | string (email) | Oui |  |
|  | `first_name` | string | Oui |  |
|  | `last_name` | string | Oui |  |
|  | `language` | string | Oui | `fr` ou `en` |
|  | `email_verified` | boolean | Oui |  |
| `VerifyEmailIn` | `token` | string | Oui |  |
| `LoginIn` | `email` | string (email) | Oui |  |
|  | `password` | string | Oui |  |
| `TokenOut` | `access_token` | string (JWT) | Oui |  |
|  | `token_type` | string | Oui | `bearer` |
|  | `expires_in` | integer | Oui | secondes, 900 au maximum |
| `ForgotPasswordIn` | `email` | string (email) | Oui |  |
| `ResetPasswordIn` | `token` | string | Oui | usage unique, valable 30 minutes |
|  | `new_password` | string | Oui | 12 caractères minimum |

### 8.3 Catalogue

| Schéma | Champ | Type | Obligatoire | Contraintes |
| :---- | :---- | :---- | :---- | :---- |
| `ProductSummary` | `id` | string (uuid) | Oui |  |
|  | `sku` | string | Oui | unique |
|  | `name_fr`, `name_en` | string | Oui |  |
|  | `brand` | string ou null | Non |  |
|  | `price_cents` | integer | Oui | ≥ 0 |
|  | `main_image_url` | string ou null | Non |  |
|  | `category_id` | string (uuid) ou null | Non |  |
| `ProductDetail` | champs de `ProductSummary` |  |  |  |
|  | `description_fr`, `description_en` | string ou null | Non |  |
|  | `specs` | object | Oui | caractéristiques techniques (JSONB) |
|  | `images` | array de `ImageOut` | Oui |  |
|  | `availability` | array de `StoreAvailability` | Oui |  |
| `ImageOut` | `id` | string (uuid) | Oui |  |
|  | `url` | string | Oui |  |
|  | `alt_fr`, `alt_en` | string ou null | Non |  |
|  | `position` | integer | Oui |  |
| `StoreAvailability` | `store_id` | string (uuid) | Oui |  |
|  | `store_name` | string | Oui |  |
|  | `status` | string | Oui | `in_stock`, `low_stock`, `out_of_stock` |
| `CategoryNode` | `id` | string (uuid) | Oui |  |
|  | `slug` | string | Oui |  |
|  | `name_fr`, `name_en` | string | Oui |  |
|  | `children` | array de `CategoryNode` | Oui |  |
| `StoreOut` | `id` | string (uuid) | Oui |  |
|  | `name`, `address` | string | Oui |  |
|  | `phone` | string ou null | Non |  |
|  | `opening_hours` | object | Oui |  |

La disponibilité est calculée à partir des stocks réels; la réponse publique ne donne que le statut, jamais les quantités (A-CAT-02).

### 8.4 Administration

| Schéma | Champ | Type | Obligatoire | Contraintes |
| :---- | :---- | :---- | :---- | :---- |
| `ProductCreate` | `sku` | string | Oui | 1 à 64 caractères, unique |
|  | `name_fr`, `name_en` | string | Oui | non vide |
|  | `description_fr`, `description_en` | string ou null | Non |  |
|  | `brand` | string ou null | Non |  |
|  | `price_cents` | integer | Oui | ≥ 0 |
|  | `specs` | object | Non | `{}` par défaut |
|  | `category_id` | string (uuid) ou null | Non |  |
|  | `is_active` | boolean | Non | `true` par défaut |
| `ProductUpdate` | mêmes champs que `ProductCreate` |  | Non | tous facultatifs |
| `ProductAdminOut` | champs de `ProductDetail` |  |  |  |
|  | `is_active` | boolean | Oui |  |

Aucun schéma de réponse **ne doit** contenir `password_hash`, `mfa_secret` ni `pickup_token_hash`. La conformité des modèles de sortie réels reste à vérifier. Pour `ProductUpdate`, le document conserve le `PUT` proposé, mais des champs tous facultatifs correspondent à une sémantique de modification partielle : **décision ouverte** entre `PUT` complet (champs obligatoires) et `PATCH` partiel. Ne pas changer la méthode sans validation.

---

## 9\. Exemples contractuels — à comparer aux réponses réelles

### 9.1 Inscription

Requête : `POST /api/v1/auth/register`

```json
{
  "email": "marie.tremblay@example.com",
  "password": "un-mot-de-passe-solide-2026",
  "first_name": "Marie",
  "last_name": "Tremblay",
  "language": "fr",
  "privacy_consent": true
}
```

Réponse : `201 Created`

```json
{
  "id": "3f1c2e4a-8b5d-4c7e-9a10-2d6f5b8c1e34",
  "email": "marie.tremblay@example.com",
  "first_name": "Marie",
  "last_name": "Tremblay",
  "language": "fr",
  "email_verified": false
}
```

### 9.2 Connexion

Requête : `POST /api/v1/auth/login`

```json
{ "email": "marie.tremblay@example.com", "password": "un-mot-de-passe-solide-2026" }
```

Réponse : `200 OK`, avec l'en-tête `Set-Cookie: refresh_token=...; HttpOnly; Secure; ...`

```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 900 }
```

### 9.3 Liste de produits

Requête : `GET /api/v1/products?page=1&size=20&sort=price_asc`

Réponse : `200 OK`

```json
{
  "items": [
    {
      "id": "b7a9c1d2-4e3f-4a5b-8c6d-7e8f9a0b1c2d",
      "sku": "PERC-18V-001",
      "name_fr": "Perceuse sans fil 18 V",
      "name_en": "18 V cordless drill",
      "brand": "ExempleMarque",
      "price_cents": 8999,
      "main_image_url": "https://exemple.invalid/images/perc-18v-001.jpg",
      "category_id": "c0d1e2f3-a4b5-4c6d-9e7f-8a9b0c1d2e3f"
    }
  ],
  "page": 1,
  "size": 20,
  "total": 152
}
```

### 9.4 Disponibilité d'un produit

Requête : `GET /api/v1/products/b7a9c1d2-4e3f-4a5b-8c6d-7e8f9a0b1c2d/availability`

Réponse : `200 OK`

```json
[
  { "store_id": "11111111-1111-4111-8111-111111111111", "store_name": "Saint-Jérôme", "status": "in_stock" },
  { "store_id": "22222222-2222-4222-8222-222222222222", "store_name": "Sainte-Agathe-des-Monts", "status": "low_stock" },
  { "store_id": "33333333-3333-4333-8333-333333333333", "store_name": "Mont-Tremblant", "status": "out_of_stock" }
]
```

### 9.5 Erreur de validation

Réponse : `422 Unprocessable Entity`

```json
{
  "code": "validation_error",
  "message": "Les données envoyées sont invalides.",
  "errors": [
    { "field": "body.password", "message": "Le mot de passe doit contenir au moins 12 caractères.", "type": "string_too_short" }
  ],
  "request_id": "9d2f6c1a-7b3e-4f8a-a1c5-0e4d3b2a1f90"
}
```

### 9.6 Ressource introuvable

Réponse : `404 Not Found`

```json
{
  "code": "not_found",
  "message": "Ressource introuvable.",
  "details": null,
  "request_id": "5a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"
}
```

### 9.7 Trop de requêtes

Réponse : `429 Too Many Requests`, avec `Retry-After: 900`

```json
{
  "code": "rate_limited",
  "message": "Trop de tentatives. Réessayez plus tard.",
  "details": { "retry_after_seconds": 900 },
  "request_id": "7c8d9e0f-1a2b-4c3d-9e4f-5a6b7c8d9e0f"
}
```

---

## 10\. Routes contractuelles cibles (L2 et L3)

Elles proviennent de la liste A.7. Les jalons suivent la portée de L2 et de L3 de A.11. **Ces routes font partie du contrat cible global et sont prévisionnelles : elles ne doivent pas être présentées comme disponibles.**

### 10.1 Prévues pour L2 (transactions et RAG)

| Route | Accès | Exigences | Objet |
| :---- | :---- | :---- | :---- |
| `GET/PUT /cart` | Client | A-ORD-01, A-ORD-02 | Panier côté serveur et magasin de cueillette |
| `POST /cart/items`, `DELETE /cart/items/{id}` | Client | A-ORD-01, RA-A-07 | Ajouter ou retirer un article (quantité de 1 à 20\) |
| `POST /checkout` | Client | A-ORD-03, A-ORD-04 | Recalcul des prix, réservation du stock, intention de paiement |
| `POST /webhooks/stripe` | Stripe seulement | A-ORD-05, A-ORD-06 | Confirmation de paiement; en-tête `Stripe-Signature` vérifié; traitement idempotent |
| `GET /orders`, `GET /orders/{id}` | Client (propriétaire) | A-ORD-07 | Historique et détail des commandes |
| `GET /orders/{id}/pickup-qr` | Client (propriétaire) | A-PCK-01 | Jeton de cueillette signé pour le code QR |
| `GET /staff/orders?store=` | Commis ou gérant (son magasin) | A-INV-05 | Commandes à préparer |
| `POST /staff/orders/{id}/ready` | Commis ou gérant (son magasin) | A-INV-05, A-ORD-07 | Marquer la commande prête |
| `POST /staff/pickups/validate` | Commis ou gérant (son magasin) | A-PCK-02, A-PCK-03 | Valider la cueillette |
| `GET /staff/inventory` | Commis ou gérant | A-INV-01 | Consulter le stock |
| `POST /staff/inventory/receive` | Commis ou gérant | A-INV-02 | Réception de marchandises |
| `GET/PUT /me` | Client | A-PRV-01 | Profil du client — **implémenté** en `GET /auth/me` et `PATCH /auth/me` (modification partielle, comme DEC-03 ; #68) |
| `POST /chat/messages`, `POST /chat/feedback` | Public (débit limité) | section 7, A.9 | Agent « Conseiller Laurentien » et rétroaction |

### 10.2 Prévues pour L3 (version finale)

| Route | Accès | Exigences | Objet |
| :---- | :---- | :---- | :---- |
| `POST /auth/mfa/setup`, `POST /auth/mfa/verify` | Personnel | A-AUTH-06 | MFA TOTP |
| `POST /orders/{id}/cancel` | Client (propriétaire) | A-ORD-09, RA-A-05 | Annulation à l'état `paid` et remboursement (test) |
| `POST /staff/inventory/adjust` | Commis ou gérant | A-INV-03 | Ajustement avec motif |
| `/admin/users` (CRUD) | Administrateur | A-ADM-02 | Comptes du personnel, rôles, magasin |
| `/admin/promotions` (CRUD) | Administrateur | A-ORD-10 | Promotions |
| `GET /admin/reports/*` | Administrateur | A-ADM-03 | Rapports et tableau de bord |
| `GET /admin/audit-logs` | Administrateur | A-ADM-04 | Journal d'audit (route ajoutée, absente de A.7) |
| `POST /admin/kb/reindex` | Administrateur | A-ADM-05 | Relancer l'ingestion de la base de connaissances |
| `GET /me/export` | Client | A-PRV-02 | Export des renseignements personnels (JSON) |
| `POST /me/delete-request` | Client | A-PRV-03 | Demande de suppression et anonymisation |

Des filtres supplémentaires sur `GET /products` (fourchette de prix, marque, disponibilité dans un magasin) sont prévus par A-CAT-04.

---

## 11. Matrice de conformité OpenAPI (à compléter lors de l'audit technique)

| Domaine | Contrat documentaire | OpenAPI généré | Tests / preuve | Statut |
| :--- | :--- | :--- | :--- | :--- |
| Authentification L1 | §7.1, §7.5 | Comparé (§18.1) | 119 tests ; CI `api-ci` | **Vérifié** — écarts consignés |
| Catalogue / recherche | §7.2 | Comparé (§18.1) | PR #29 (CI verte) | **Vérifié** (non fusionné) |
| Administration produits / catégories | §7.3, §7.5 | Comparé (§18.1) | PR #29 (CI verte) | **Vérifié** (non fusionné) — écarts consignés |
| Santé | §7.4 | `GET /health` (hors `/api/v1`) | CI `api-ci` (démarrage production) | **Vérifié** |
| Formats d'erreur / sécurité | §§2–6, §8 | Comparé (§18.2) | — | **Écart** : `ErrorOut` non implémenté (ADR-008) |
| Routes L2/L3 | §§10, 15–17 | À comparer lors de leur implémentation | À renseigner par domaine | Contractuel, non vérifié |

**Méthode :** exporter le schéma OpenAPI depuis l'application FastAPI effectivement exécutée, puis comparer méthodes, chemins, paramètres, schémas, codes de réponse et exigences de sécurité. Consigner les différences et rattacher les tests et preuves (commit, exécution CI, URL de démonstration). Ne pas inventer de résultat de test ou de fichier `openapi.json`.

## 12. Compatibilité des trois clients

| Client | Authentification cible | Points à confirmer |
| :--- | :--- | :--- |
| Web React/Vite | Jeton d'accès Bearer ; rafraîchissement via cookie `HttpOnly` | CORS avec identifiants, `SameSite`, CSRF, domaine et HTTPS |
| Mobile React Native/Expo | Jeton d'accès Bearer ; stockage sécurisé natif des secrets de session | Flux de rafraîchissement adapté à l'application native |
| Bureau C# WPF/.NET 8 | Jeton d'accès Bearer ; stockage protégé par le système d'exploitation | Gestion de session, révocation et renouvellement |

**Principe conservé :** les trois clients consomment l'API ; aucun n'accède directement à PostgreSQL. Les modalités natives sont des propositions à valider, pas des mécanismes attestés.

## 13. Registre des vérifications et décisions ouvertes

| ID | Élément | Nature | État / action |
| :--- | :--- | :--- | :--- |
| VER-01 | Export réel `/openapi.json` et concordance des routes | Vérification | En attente |
| VER-02 | Présence de `GET /auth/me` et schéma de sortie | Vérification | En attente |
| VER-03 | Gestionnaire d'erreurs `ErrorOut` / 422 | Vérification | En attente |
| VER-04 | Application effective des limites de débit et en-têtes | Vérification | En attente |
| DEC-01 | `SameSite`, CSRF, rotation/révocation et stratégie Web | Décision / vérification | À valider |
| DEC-02 | Stratégies de session Mobile et Bureau | Décision | À valider |
| DEC-03 | `PUT` complet ou `PATCH` partiel pour les produits | Décision | À valider |
| DEC-04 | Méthodes et schémas CRUD des catégories | Décision | À valider |
| VER-05 | Références `A-D*` et liens vers exigences officielles | Vérification documentaire | En attente |
| VER-06 | Preuves de déploiement et d'exécution L1 | Vérification | En attente |

## 14. Historique documentaire et conditions de validation

| Version | Date | Modification |
| :--- | :--- | :--- |
| 1.0 | Non renseignée | Document initial (10 sections) |
| 1.1 | 2026-11-21 | Clarification des statuts, sécurité, pagination, erreurs, traçabilité et validation OpenAPI ; routes et choix de base conservés |
| 1.2 | 2026-11-21 | Extension du contrat aux domaines L2/L3 : méthodes, schémas, erreurs, règles métier, exemples et traçabilité ; sans présumer de leur implémentation |
| 1.3 | 2026-11-21 | Conformité à l'OpenAPI réellement généré (§18) : routes implémentées et prévues, écarts consignés ; `PATCH` (DEC-03) et CRUD catégories/marques (DEC-04) tranchés |

**Validation finale conditionnelle :** (1) confirmer les exigences et décisions ouvertes, (2) comparer le contrat au schéma FastAPI généré, (3) rattacher tests et preuves CI, (4) faire approuver la version par le responsable du projet. L'absence de ces preuves n'empêche pas la revue documentaire, mais interdit de déclarer le contrat techniquement vérifié.


---

## 15. Contrats détaillés des fonctionnalités L2 — transactions, cueillette, stocks et agent

**Statut de toute la section : contractuel cible, non vérifié dans le code.** Les routes sont issues de l’aperçu indicatif A.7 et des exigences A.4/A.9 du cahier des charges. Les schémas, champs non imposés et codes HTTP sont **proposés**. Tous les chemins ci-dessous sont relatifs à `/api/v1`. Les erreurs 401/403/404/422/429 s’appliquent selon le contexte et ne sont pas répétées systématiquement.

### 15.1 Panier et magasin de cueillette (A-ORD-01, A-ORD-02, RA-A-07)

| Méthode et route | Entrée | Succès et schéma | Erreurs spécifiques | Règle métier |
| :--- | :--- | :--- | :--- | :--- |
| `GET /cart` | Aucune | 200 `CartOut` | 401 | Panier du client connecté uniquement |
| `PUT /cart` | `CartUpdateIn` | 200 `CartOut` | 400, 409, 422 | Magasin choisi; contrôle de disponibilité serveur |
| `POST /cart/items` | `CartItemCreateIn` | 201 `CartOut` | 404, 409, 422 | Quantité entre 1 et 20 |
| `DELETE /cart/items/{id}` | UUID de ligne | 204 sans corps | 404 | Ne peut supprimer que sa propre ligne |

| Schéma | Champs et types | Contraintes / notes |
| :--- | :--- | :--- |
| `CartUpdateIn` | `pickup_store_id: uuid` | Magasin existant ; disponibilité revérifiée au checkout |
| `CartItemCreateIn` | `product_id: uuid`, `quantity: integer` | `quantity` entre 1 et 20 ; ajout/fusion à préciser |
| `CartItemOut` | `id: uuid`, `product_id: uuid`, `quantity: integer`, `unit_price_cents: integer`, `line_total_cents: integer` | Prix indicatif recalculé côté serveur |
| `CartOut` | `id: uuid`, `pickup_store_id: uuid|null`, `items: CartItemOut[]`, `subtotal_cents: integer`, `currency: string` | `currency` proposée : `CAD`; les prix ne sont jamais fiables s'ils proviennent du client |

### 15.2 Checkout, paiement et commandes (A-ORD-03 à A-ORD-10)

| Méthode et route | Entrée | Succès et schéma | Erreurs spécifiques | Règle métier |
| :--- | :--- | :--- | :--- | :--- |
| `POST /checkout` | `CheckoutIn` | 200 ou 201 `CheckoutOut` **à décider** | 409 stock insuffisant, 422 | Prix, TPS 5 % et TVQ 9,975 % recalculés au serveur; stock réservé atomiquement |
| `POST /webhooks/stripe` | Corps brut Stripe + `Stripe-Signature` | 200 `WebhookAckOut` proposé | 400 signature invalide | Signature sur corps brut, déduplication par identifiant Stripe, transaction atomique |
| `GET /orders` | `page`, `size`, filtres proposés | 200 `Page[OrderSummary]` | 401 | Seulement les commandes du client |
| `GET /orders/{id}` | UUID | 200 `OrderDetail` | 404 | Contrôle de propriété |
| `POST /orders/{id}/cancel` | `OrderCancelIn` proposé | 200 `OrderDetail` | 409 transition impossible | Préparation non commencée; remboursement test et libération de stock; L3 selon jalon actuel |

| Schéma | Champs et types | Contraintes / notes |
| :--- | :--- | :--- |
| `CheckoutIn` | `cart_id: uuid` (proposé) | Pas de prix fourni par le client ; clé d'idempotence de requête à décider |
| `CheckoutOut` | `order_id: uuid`, `status: OrderStatus`, `payment_provider: string`, `payment_redirect_url: string|null`, `payment_client_secret: string|null`, `reservation_expires_at: date-time` | Un seul mécanisme de paiement exposé selon Stripe Checkout ou Payment Intents; **choix à valider**; ne jamais exposer de secret serveur Stripe |
| `WebhookAckOut` | `received: boolean` | Accusé de réception uniquement, sans donnée sensible |
| `OrderSummary` | `id: uuid`, `number: string`, `status: OrderStatus`, `pickup_store_id: uuid`, `total_cents: integer`, `created_at: date-time` | `number` est une référence métier proposée |
| `OrderItemOut` | `product_id: uuid`, `sku: string`, `name_fr: string`, `name_en: string`, `quantity: integer`, `unit_price_cents: integer`, `line_total_cents: integer` | Instantané de commande, indépendant du catalogue futur |
| `OrderDetail` | champs `OrderSummary`, `items: OrderItemOut[]`, `subtotal_cents: integer`, `discount_cents: integer`, `gst_cents: integer`, `qst_cents: integer`, `pickup_code_available: boolean`, `status_history: OrderStatusEvent[]` | Total recalculé et arrondis documentés lors de l'implémentation |
| `OrderStatusEvent` | `status: OrderStatus`, `changed_at: date-time`, `actor_id: uuid|null` | Historique horodaté et auteur selon A-ORD-07 |
| `OrderCancelIn` | `reason: string|null` | Proposition ; ne remplace pas les vérifications d'état |
| `OrderStatus` | enum `pending_payment`, `paid`, `preparing`, `ready_for_pickup`, `picked_up`, `cancelled`, `refunded`, `expired` | Transitions contrôlées côté serveur, jamais choisies librement par le client |

**Contraintes transactionnelles :** réservation de stock avec verrouillage concurrent (`SELECT ... FOR UPDATE` ou mécanisme équivalent validé), expiration et libération des réservations non payées, webhook signé et idempotent, aucune confirmation de paiement sur simple retour navigateur. Les choix d'arrondi des taxes, de clé d'idempotence et de fournisseur Stripe sont à confirmer. Les courriels de confirmation et de disponibilité (A-ORD-08, Should) sont des effets métier, non des endpoints supplémentaires obligatoires.

### 15.3 Cueillette QR et préparation (A-PCK-01 à 04, A-INV-05)

| Méthode et route | Entrée | Succès et schéma | Erreurs spécifiques | Règle métier |
| :--- | :--- | :--- | :--- | :--- |
| `GET /orders/{id}/pickup-qr` | UUID | 200 `PickupQrOut` | 404, 409 | Commande propre au client, prête à récupérer |
| `GET /staff/orders` | `store` (UUID), `page`, `size`, `status` (proposé) | 200 `Page[StaffOrderSummary]` | 403 | Magasin autorisé du membre du personnel |
| `POST /staff/orders/{id}/ready` | UUID | 200 `StaffOrderSummary` | 403, 404, 409 | Transition autorisée vers `ready_for_pickup` |
| `POST /staff/pickups/validate` | `PickupValidationIn` | 200 `PickupValidationOut` | 400, 403, 404, 409 | QR signé/expirant, magasin conforme, usage unique atomique |

| Schéma | Champs et types | Contraintes / notes |
| :--- | :--- | :--- |
| `PickupQrOut` | `order_id: uuid`, `token: string`, `expires_at: date-time`, `qr_payload: string` | Champs proposés ; jeton signé et limité au magasin, à ne pas journaliser |
| `StaffOrderSummary` | `id: uuid`, `number: string`, `status: OrderStatus`, `pickup_store_id: uuid`, `items: OrderItemOut[]` | Informations personnelles minimisées |
| `PickupValidationIn` | `token: string|null`, `order_number: string|null`, `last_name: string|null` | Soit jeton QR, soit numéro + nom; validation croisée et limitation de débit |
| `PickupValidationOut` | `order_id: uuid`, `status: string`, `picked_up_at: date-time`, `staff_user_id: uuid` | `status = picked_up`; une seconde validation échoue |

**A-PCK-04 (Should) :** signalement après 7 jours et possibilité d'annulation/remboursement par le gérant. Aucun chemin n'est imposé par A.7 : endpoints éventuels `GET /staff/orders/overdue` et `POST /staff/orders/{id}/cancel` **proposés, à décider**.

### 15.4 Inventaire et mouvements (A-INV-01 à 07)

| Méthode et route | Entrée | Succès et schéma | Erreurs spécifiques | Règle métier |
| :--- | :--- | :--- | :--- | :--- |
| `GET /staff/inventory` | `store_id`, `page`, `size`, `q` proposés | 200 `Page[InventoryItemOut]` | 403 | Magasin dans le périmètre du personnel |
| `POST /staff/inventory/receive` | `InventoryReceiveIn` | 201 `StockMovementBatchOut` | 403, 409, 422 | Réception et journal de mouvements atomiques |
| `POST /staff/inventory/adjust` | `InventoryAdjustIn` | 201 `StockMovementOut` | 403, 409, 422 | Motif obligatoire, autorisations et approbation selon politique validée |

| Schéma | Champs et types | Contraintes / notes |
| :--- | :--- | :--- |
| `InventoryItemOut` | `product_id: uuid`, `store_id: uuid`, `on_hand: integer`, `reserved: integer`, `available: integer`, `reorder_threshold: integer` | Quantités accessibles uniquement au personnel autorisé |
| `InventoryReceiveLineIn` | `product_id: uuid`, `quantity: integer` | Quantité strictement positive |
| `InventoryReceiveIn` | `store_id: uuid`, `lines: InventoryReceiveLineIn[]`, `reference: string|null` | Liste non vide, magasin autorisé |
| `InventoryAdjustIn` | `store_id: uuid`, `product_id: uuid`, `quantity_delta: integer`, `reason: string` | Variation non nulle, motif non vide; interdiction de stock négatif |
| `StockMovementOut` | `id: uuid`, `store_id: uuid`, `product_id: uuid`, `quantity_delta: integer`, `reason: string`, `actor_id: uuid`, `created_at: date-time` | Piste d'audit |
| `StockMovementBatchOut` | `movements: StockMovementOut[]` | Résultat de réception proposé |

**A-INV-04/06/07 (Should/Could) :** alertes de seuil, retours et transferts entre magasins sont dans le périmètre fonctionnel global. Les chemins dédiés (`GET /staff/inventory/low-stock`, `POST /staff/returns`, `POST /staff/transfers`, `POST /staff/transfers/{id}/confirm`) sont **des propositions non arrêtées** ; leurs contrats détaillés devront être approuvés avant développement.

### 15.5 Profil et agent conversationnel (A-PRV-01, A.9)

| Méthode et route | Entrée | Succès et schéma | Erreurs spécifiques | Règle métier |
| :--- | :--- | :--- | :--- | :--- |
| `GET /me` | Aucune | 200 `ProfileOut` | 401 | Profil du titulaire |
| `PUT /me` | `ProfileUpdateIn` | 200 `ProfileOut` | 401, 422 | Champs modifiables limités |
| `POST /chat/messages` | `ChatMessageIn` | 200 `ChatMessageOut` proposé | 422, 429, 503 | Réponse fondée sur la base documentaire; absence de réponse fiable signalée |
| `POST /chat/feedback` | `ChatFeedbackIn` | 201 `ChatFeedbackOut` proposé | 404, 422, 429 | Retour utilisateur, aucune donnée personnelle superflue |

| Schéma | Champs et types | Contraintes / notes |
| :--- | :--- | :--- |
| `ProfileOut` | `id: uuid`, `first_name: string`, `last_name: string`, `language: string`, `communication_preferences: object` | `fr` ou `en`; consentements à tracer séparément |
| `ProfileUpdateIn` | `first_name: string|null`, `last_name: string|null`, `language: string|null`, `communication_preferences: object|null` | Schéma proposé, sémantique de `PUT` à valider |
| `ChatMessageIn` | `message: string`, `session_id: uuid|null`, `language: string|null` | Taille maximale et rétention à fixer; limiter les données sensibles |
| `ChatSourceOut` | `document_id: uuid|null`, `title: string`, `reference: string|null` | Citations issues de documents réellement retrouvés |
| `ChatMessageOut` | `session_id: uuid`, `message_id: uuid`, `answer: string`, `sources: ChatSourceOut[]`, `grounded: boolean` | `grounded` proposé; réponse de repli si information non trouvée |
| `ChatFeedbackIn` | `message_id: uuid`, `rating: integer`, `comment: string|null` | Échelle de notation à approuver |
| `ChatFeedbackOut` | `id: uuid`, `received: boolean` | Aucun contenu sensible retourné |

Le flux de réponse en continu (*streaming*) n'est **pas spécifié** dans le contrat source : s'il est retenu, définir explicitement un endpoint, son type de contenu (`text/event-stream` par exemple), les événements et la gestion des erreurs. Ne pas supposer qu'il existe.

## 16. Contrats détaillés des fonctionnalités L3 — administration, MFA, vie privée

**Statut : cible contractuelle non vérifiée.** La répartition L3 suit le document initial et A.11; certaines exigences sont Should/Could. Les méthodes CRUD et les schémas ci-dessous sont proposés lorsque le cahier des charges ne les impose pas.

### 16.1 Authentification multifacteur du personnel (A-AUTH-06)

| Route | Requête | Réponse proposée | Sécurité |
| :--- | :--- | :--- | :--- |
| `POST /auth/mfa/setup` | Session authentifiée | 200 `MfaSetupOut` | Accès personnel; étape de réauthentification à décider |
| `POST /auth/mfa/verify` | `MfaVerifyIn` | 200 `MfaVerifyOut` | Code TOTP limité en tentatives, anti-rejeu |

`MfaSetupOut` : `provisioning_uri: string`, `secret_display: string` (uniquement à l'enrôlement, jamais journalisé). `MfaVerifyIn` : `code: string`. `MfaVerifyOut` : `verified: boolean`. La séparation entre activation MFA et défi de connexion est une **décision de conception ouverte**; ces deux routes indicatives ne suffisent pas à décrire un parcours complet de connexion MFA.

### 16.2 Administration des utilisateurs, promotions et rapports (A-ADM-02 à 05, A-ORD-10)

| Route cible | Entrée | Réponse cible | Contrôle |
| :--- | :--- | :--- | :--- |
| `GET /admin/users` | `page`, `size`, `role`, `store_id` proposés | 200 `Page[StaffUserOut]` | Administrateur |
| `POST /admin/users` | `StaffUserCreateIn` | 201 `StaffUserOut` | Administrateur; attribution de rôle et magasin |
| `GET /admin/users/{id}` | UUID | 200 `StaffUserOut` | Administrateur |
| `PUT /admin/users/{id}` | `StaffUserUpdateIn` | 200 `StaffUserOut` | Administrateur; sémantique PUT/PATCH à décider |
| `DELETE /admin/users/{id}` | UUID | 204 | Désactivation proposée, pas d'effacement d'audit |
| `GET /admin/promotions` | `page`, `size` | 200 `Page[PromotionOut]` | Administrateur |
| `POST /admin/promotions` | `PromotionIn` | 201 `PromotionOut` | Administrateur |
| `GET /admin/promotions/{id}` | UUID | 200 `PromotionOut` | Administrateur |
| `PUT /admin/promotions/{id}` | `PromotionIn` | 200 `PromotionOut` | Administrateur |
| `DELETE /admin/promotions/{id}` | UUID | 204 | Désactivation proposée |
| `GET /admin/reports/*` | Période, magasin, type | 200 `ReportOut` proposé | Administrateur; **chemins précis à définir** |
| `GET /admin/audit-logs` | `page`, `size`, dates, acteur | 200 `Page[AuditLogOut]` proposé | Administrateur; journal sensible |
| `POST /admin/kb/reindex` | `KbReindexIn` proposé | 202 `JobOut` proposé | Administrateur; traitement asynchrone à confirmer |

| Schéma | Champs et types proposés | Contraintes |
| :--- | :--- | :--- |
| `StaffUserCreateIn` | `email: email`, `first_name: string`, `last_name: string`, `role: string`, `store_id: uuid|null` | Rôles autorisés, affectation contrôlée; aucune valeur de mot de passe en réponse |
| `StaffUserUpdateIn` | Champs modifiables de `StaffUserCreateIn`, `is_active: boolean` | Champs optionnels seulement si PATCH choisi |
| `StaffUserOut` | `id: uuid`, `email: email`, `role: string`, `store_id: uuid|null`, `is_active: boolean` | Ne pas exposer `password_hash` ni secret MFA |
| `PromotionIn` | `name: string`, `discount_type: string`, `discount_value: integer`, `starts_at: date-time`, `ends_at: date-time`, `product_ids: uuid[]`, `category_ids: uuid[]`, `usage_limit: integer|null`, `code: string|null` | Pourcentage ou montant fixe; unité du pourcentage et combinaison des cibles à décider; limite d'utilisation atomique |
| `PromotionOut` | champs de `PromotionIn`, `id: uuid`, `is_active: boolean`, `usage_count: integer` | Aucune utilisation au-delà de la limite, même concurrente |
| `ReportOut` | `period_start: date-time`, `period_end: date-time`, `metrics: object` | Métriques et agrégations à spécifier par rapport |
| `AuditLogOut` | `id: uuid`, `actor_id: uuid|null`, `action: string`, `resource_type: string`, `resource_id: uuid|null`, `created_at: date-time` | Journal sans secrets; filtre d'accès strict |
| `KbReindexIn` | `scope: string|null` | Paramètre proposé, validation nécessaire |
| `JobOut` | `job_id: uuid`, `status: string` | Ne pas promettre de suivi de job sans route prévue |

### 16.3 Vie privée (A-PRV-02, A-PRV-03, A-PRV-04)

| Route | Entrée | Réponse cible | Règle métier |
| :--- | :--- | :--- | :--- |
| `GET /me/export` | Session du client | 200 `PersonalDataExportOut` ou fichier JSON | Données du titulaire seulement, `Cache-Control: no-store` |
| `POST /me/delete-request` | `DeleteRequestIn` proposé | 202 `DeleteRequestOut` proposé | Traitement différé, contraintes de conservation légale |

`PersonalDataExportOut` : `profile: object`, `orders: array`, `consents: array`, `generated_at: date-time` (**structure proposée**). `DeleteRequestIn` : `confirmation: boolean` (**proposé**). `DeleteRequestOut` : `request_id: uuid`, `status: string`, `created_at: date-time` (**proposé**). Le bandeau de témoins et les consentements de communication (A-PRV-04) relèvent du parcours web et de la persistance des choix; un endpoint dédié n'est pas imposé par A.7. Tout endpoint de consentement ajouté doit être défini et approuvé séparément.

## 17. Exemples JSON L2/L3, matrice de traçabilité et décisions ouvertes

### 17.1 Exemples représentatifs — contractuels, non exécutés

**Checkout (L2)** — `POST /api/v1/checkout`, réponse cible indicative `200 OK` (statut HTTP à décider) :

```json
{
  "order_id": "5dbb0a7e-47a4-46b6-9117-25b8bd8910a4",
  "status": "pending_payment",
  "payment_provider": "stripe",
  "payment_redirect_url": "https://checkout.stripe.com/example-placeholder",
  "payment_client_secret": null,
  "reservation_expires_at": "2026-11-21T15:15:00Z"
}
```

**Commande (L2)** — extrait de `GET /api/v1/orders/{id}` :

```json
{
  "id": "5dbb0a7e-47a4-46b6-9117-25b8bd8910a4",
  "number": "QL-EXEMPLE-001",
  "status": "paid",
  "pickup_store_id": "11111111-1111-4111-8111-111111111111",
  "total_cents": 11496,
  "created_at": "2026-11-21T15:00:00Z",
  "items": [{"product_id": "b7a9c1d2-4e3f-4a5b-8c6d-7e8f9a0b1c2d", "sku": "PERC-18V-001", "name_fr": "Perceuse", "name_en": "Drill", "quantity": 1, "unit_price_cents": 9999, "line_total_cents": 9999}],
  "subtotal_cents": 9999,
  "discount_cents": 0,
  "gst_cents": 500,
  "qst_cents": 997,
  "pickup_code_available": false,
  "status_history": [{"status": "paid", "changed_at": "2026-11-21T15:00:00Z", "actor_id": null}]
}
```

Les chiffres de cet exemple illustrent uniquement la forme de la réponse et un calcul simplifié; ils ne fixent pas la politique d'arrondi fiscale.

**Validation de cueillette (L2)** — `POST /api/v1/staff/pickups/validate` :

```json
{ "token": "jeton-signe-exemple", "order_number": null, "last_name": null }
```

Réponse illustrative :

```json
{ "order_id": "5dbb0a7e-47a4-46b6-9117-25b8bd8910a4", "status": "picked_up", "picked_up_at": "2026-11-21T17:00:00Z", "staff_user_id": "33333333-3333-4333-8333-333333333333" }
```

**Réception de stock (L2)** — `POST /api/v1/staff/inventory/receive` :

```json
{ "store_id": "11111111-1111-4111-8111-111111111111", "lines": [{"product_id": "b7a9c1d2-4e3f-4a5b-8c6d-7e8f9a0b1c2d", "quantity": 5}], "reference": "BON-EXEMPLE" }
```

**Agent (L2)** — `POST /api/v1/chat/messages` :

```json
{ "message": "Quelle perceuse convient à un usage domestique ?", "session_id": null, "language": "fr" }
```

Réponse illustrative :

```json
{ "session_id": "6c8d65ac-5e50-4c19-a981-6fbc76c2b5df", "message_id": "3f1c2e4a-8b5d-4c7e-9a10-2d6f5b8c1e34", "answer": "Je peux vous aider à comparer les caractéristiques des produits du catalogue.", "sources": [], "grounded": false }
```

**Promotion (L3)** — `POST /api/v1/admin/promotions` :

```json
{ "name": "Promotion exemple", "discount_type": "fixed", "discount_value": 500, "starts_at": "2026-12-01T00:00:00Z", "ends_at": "2026-12-31T23:59:59Z", "product_ids": [], "category_ids": [], "usage_limit": 100, "code": "EXEMPLE500" }
```

### 17.2 Traçabilité de bout en bout

| Domaine | Exigences principales du cahier | Sections contractuelles | Jalon initial | Statut technique |
| :--- | :--- | :--- | :--- | :--- |
| Comptes, authentification | A-AUTH-01 à 07 | §§2, 7.1, 8.2, 16.1 | L1 + L3 MFA | À vérifier |
| Catalogue, recherche, magasins | A-CAT-01 à 04 | §§4, 7.2, 8.3, 10 | L1 + compléments | À vérifier |
| Administration produits | A-ADM-01 | §§7.3, 7.5, 8.4 | L1 | À vérifier |
| Panier | A-ORD-01, 02 | §15.1 | L2 | Cible |
| Paiement, commandes, annulation, promotions | A-ORD-03 à 10 | §§15.2, 16.2 | L2 + L3 | Cible |
| Cueillette et préparation | A-PCK-01 à 04, A-INV-05 | §15.3 | L2 + compléments | Cible |
| Inventaire, réception, ajustement | A-INV-01 à 07 | §15.4 | L2 + L3/optionnel | Cible |
| Profil et confidentialité | A-PRV-01 à 04 | §§15.5, 16.3 | L2 + L3 | Cible |
| Agent RAG et rétroaction | A.9 | §15.5 | L2 | Cible |
| Utilisateurs, rapports, audit, connaissances | A-ADM-02 à 05 | §16.2 | L3 | Cible |

### 17.3 Décisions contractuelles à approuver avant génération de l'OpenAPI cible

| ID | Décision ouverte | Pourquoi |
| :--- | :--- | :--- |
| API-01 | Stripe Checkout ou Payment Intents, statut HTTP et schéma exact du checkout | Éviter deux contrats incompatibles |
| API-02 | Politique de taxes/arrondis, remises, devise et champs financiers | Cohérence des totaux et remboursements |
| API-03 | Idempotence checkout, réservation, expiration et réponse webhook | Cohérence en concurrence et après reprise |
| API-04 | Cycle de vie du QR, durée, rotation et recherche manuelle | Sécurité de la cueillette |
| API-05 | Sémantique PUT/PATCH et opérations CRUD manquantes | Précision des mises à jour |
| API-06 | Flux MFA complet, enrôlement et défi de connexion | Authentification du personnel |
| API-07 | Format de réponse RAG, citations, streaming éventuel | Compatibilité des clients |
| API-08 | Chemins précis des rapports, retours, transferts, alertes et consentements | Couverture des exigences Should/Could |
| API-09 | Rétention, export, suppression et accès aux données personnelles | Protection des renseignements personnels |
| API-10 | Harmonisation schémas et erreurs avec OpenAPI FastAPI réel | Contrat exploitable et testable |

**Critère de complétude documentaire :** toutes les fonctionnalités Must de A.4/A.9 disposent d'un chemin ou d'une décision explicite; les fonctionnalités Should/Could sont identifiées sans inventer de route officielle. **Critère de validation technique, différé :** génération de `/openapi.json`, comparaison des routes et schémas, tests de contrat, validation de sécurité et approbation des décisions ouvertes. Le présent Markdown n'est **pas** un export OpenAPI exécutable.

## 18. Conformité à l'OpenAPI réellement généré (L1)

Source : `GET /openapi.json` de l'API exécutée au commit `852486c` (branche `feature/l1-catalogue`,
**PR #29, non fusionnée**), exporté dans [`docs/api/openapi-l1.json`](../api/openapi-l1.json) (OpenAPI
3.1.0, API `0.1.0`, 34 opérations). L'OpenAPI fait foi pour les routes implémentées (§ en-tête).

### 18.1 Routes implémentées

| Route | Exigence | Contrat | Écart constaté |
|---|---|---|---|
| `POST /auth/register` | A-AUTH-01 | §7.1 : 201 `UserOut` | **202** et message générique (pas d'énumération) ; champ `accept_privacy_policy` (+ `marketing_opt_in`) |
| `POST /auth/verify-email` · `POST /auth/verify-email/resend` | A-AUTH-01 | §7.5 : 204 | **200** ; route `resend` ajoutée |
| `POST /auth/login` | A-AUTH-02, 07 | 200 `TokenOut` ; 429 | Verrouillage en **423** (ADR-008 : 429 prévu) ; réponse de défi MFA possible ; `mfa_setup_required` |
| `POST /auth/refresh` · `POST /auth/logout` | A-AUTH-02 | §7.1 | Conformes (cookie `ql_refresh`, chemin `/api/v1/auth`) |
| `GET /auth/me` | — | Absente du contrat | **Ajoutée** : `role`, `is_email_verified`, `mfa_enabled`, `store_ids` |
| `PATCH /auth/me` | A-PRV-01 | §10.1 : `PUT /me` | **`PATCH`** (modification partielle) sous `/auth` ; champs `first_name`, `last_name`, `language`, `marketing_opt_in` ; courriel, rôle et mot de passe refusés (422) ; consentement marketing tracé dans `consents` ; `GET /auth/me` expose `marketing_opt_in` |
| `POST /auth/password/forgot` · `POST /auth/password/reset` | A-AUTH-04 | 202 · 204 | `reset` renvoie **200** |
| `POST /auth/mfa/setup` · `/enable` · `/verify` | A-AUTH-06 | §10.2 (L3) | **Implémentées dès le L1** (en avance) |
| `GET /categories` · `GET /stores` | A-CAT-01, 02 | §7.2 | Conformes (listes non paginées) |
| `GET /products` | A-CAT-01 | §7.2 | Conforme ; paramètres ajoutés : `lang` (tri par nom), `brand_id` (A-CAT-04) ; catégorie inconnue → 404 |
| `GET /products/{id}` · `/availability` | A-CAT-02 | §7.2 | Conformes ; aucune quantité exposée |
| `GET /search` | A-CAT-03 | §7.2 | Conforme (`q` de 1 à 100 caractères) |
| `GET`, `POST /admin/products` · `GET`, **`PATCH`**, `DELETE /admin/products/{id}` | A-ADM-01 | §7.3 : `PUT` | **`PATCH`** retenu (DEC-03 tranchée) ; `DELETE` désactive (204) |
| `POST /admin/products/{id}/images` · `DELETE …/images/{image_id}` | A-ADM-01 | §7.5 : multipart | **Corps JSON avec URL `https://`** ; téléversement de fichiers (413/415) non implémenté |
| `GET`, `POST /admin/categories` · `PATCH`, `DELETE /admin/categories/{id}` | A-ADM-01 | §7.5 : à définir | DEC-04 tranchée : `PATCH` ; `DELETE` refusé (409) si sous-catégories ou produits ; cycle → 422 |
| `GET`, `POST /admin/brands` · `PATCH`, `DELETE /admin/brands/{id}` | A-ADM-01 | Absentes | **Ajoutées** (ADR-004) ; `DELETE` désactive |
| `GET /health` | ENF-13 | §7.4 | Conforme |

### 18.2 Écarts transversaux

- **Format des erreurs** : l'API renvoie `{"detail": {"code", "message"}}` (422 : `errors[{field, reason}]`),
  sans `request_id` ni `X-Request-ID`. Le format `ErrorOut` du §6 est **prévu** (ADR-008, sous-lot 0.A).
- **Schémas** : `ProductSummary`, `ProductDetail`, `StoreAvailability`, `CategoryNode`, `StoreOut` et
  `Page[T]` correspondent au §8.3 ; `ProductCreate` reçoit `brand_id` au lieu de `brand` (ADR-004) ;
  `ProductAdminOut` ajoute `brand_id`, `created_at`, `updated_at`.
- **Limitation de débit** : connexion et inscription (existant) ; lecture publique du catalogue à
  120 requêtes/min/IP (testé).

### 18.3 Routes prévues (non implémentées)

Toutes les routes du §10 (panier, checkout, webhooks Stripe, commandes, cueillette, stocks du personnel,
profil, agent conversationnel, administration des utilisateurs, promotions, rapports, audit, vie
privée) restent **prévues** ; aucune n'est présente dans l'OpenAPI généré.
