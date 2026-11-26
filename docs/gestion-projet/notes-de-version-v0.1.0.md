# Notes de version — v0.1.0 (L1 — Fondations) — PRÊTES À VALIDER

**Non publiées.** L'étiquette `v0.1.0` et la version GitHub seront créées **uniquement sur autorisation du
responsable**, après la fusion des PR retenues et la validation finale. Les éléments marqués *(PR #n)*
ne sont pas encore sur `main` au 22 novembre 2026 (`main` = `255e219`).

## URL publiques

| | |
|---|---|
| Site web | <https://quincaillerie-laurentienne-seven.vercel.app> |
| API | <https://quincaillerie-laurentienne-api.onrender.com> (`/health`, `/docs`, `/api/v1/...`) |
| Vidéo de démonstration | À fournir par l'équipe |

Offres gratuites (Neon, Render, Vercel). L'API se met en veille après 15 minutes d'inactivité : la
première requête peut prendre jusqu'à une minute.

## Nouveautés

### API (FastAPI 0.165, Python 3.11, PostgreSQL 16)
- **Authentification (A-AUTH-01 à 07)** : inscription avec consentement, vérification du courriel,
  connexion (JWT 15 min + cookie httpOnly avec rotation), politique de mot de passe et Argon2id,
  réinitialisation (30 min, usage unique), rôles et affectation au magasin, verrouillage progressif,
  limitation de débit par IP (non falsifiable derrière Cloudflare), MFA TOTP obligatoire du personnel.
- **Catalogue public (A-CAT-01 à 03)** : catégories, magasins, produits paginés (≤ 50) avec tris et
  filtres, fiche bilingue, disponibilité par magasin **sans quantités**, recherche plein texte FR/EN
  insensible aux accents.
- **Administration (A-ADM-01)** : produits, catégories et marques (création, PATCH, désactivation),
  images par URL https ; **téléversement d'images validé** (type réel, taille, dimensions)
  (PR #49) ; adaptateur de stockage Cloudinary signé, **inactif tant que le responsable ne l'active pas**
  *(PR #54, ADR-009)*.
- **Données** : migrations de toutes les entités Must (head `e2c9a4b7d3f1`) ; amorçage de démonstration
  (3 magasins, 157 produits, stocks) ; script des comptes de démonstration par rôle, sans mot de passe
  exposé (non exécuté en production).
- Courriels transactionnels par l'API HTTPS de Brevo (le SMTP sortant est bloqué sur Render) ; un échec
  d'envoi n'interrompt plus le parcours.

### Web (React 18, Vite)
- Accueil, catalogue avec catégories, tris et pagination, recherche, fiche produit et disponibilités,
  magasins, bascule FR/EN ; image de remplacement locale.
- Inscription, vérification du courriel, connexion (avec MFA), mot de passe oublié et réinitialisation,
  compte (PR #50) ; configuration de la MFA du personnel, administration du catalogue (`/admin` :
  noms, prix, visibilité, images) et politique de confidentialité en **ébauche à valider** *(PR #55)*.
- En-têtes de sécurité (CSP stricte, `nosniff`, `Referrer-Policy`, `Permissions-Policy`) ; `/api` relayé
  vers Render (même origine).

### Mobile (Expo SDK 58, React Native)
- Liste des produits depuis l'API en ligne, filtre par catégorie, image de remplacement.
- Délai de requête de 60 s pour couvrir le réveil de l'API *(PR #51)*.

### Bureau (.NET 8, WPF)
- Liste des produits et recherche depuis l'API en ligne ; URL et délai configurables
  (`appsettings.json` ou `QL_API_BASE_URL`) ; délai par défaut de 60 s *(PR #51)*.

### DevOps et sécurité
- `main` protégée (PR obligatoire, squash, `api-ci` et `security` obligatoires, fils résolus).
- CI : `api-ci` (ruff, pytest avec couverture sur PostgreSQL 16, Bandit, pip-audit, démarrage en mode
  production), `web-ci`, `mobile-ci`, `desktop-ci`, `security` (CodeQL Python, workflows, JS/TS, C# ;
  Gitleaks sur tout l'historique).
- Dependabot : pip, npm (web, mobile), NuGet, GitHub Actions ; secret scanning et push protection.
- Dépendances à jour au 26 novembre 2026 : `i18next` 27 (correctif de sécurité GHSA-6jcc-5g8w-32mx),
  `react-i18next` 18, Vite 8, ESLint 10, SQLAlchemy 2.1, Alembic 1.20, Uvicorn 0.54, `argon2-cffi` 25,
  TypeScript 7 (mobile) ; Node.js **22.13 ou plus** requis pour le web (PR #24, #25, #44, #45, #47, #57 à #61).
- Déploiement automatique de l'API (Render, migrations et amorçage au démarrage) et du web (Vercel) à
  chaque fusion sur `main`.
- Distribution du bureau : `desktop-release` produit un exécutable Windows autonome (ZIP + SHA-256) et
  crée la version GitHub en brouillon à la poussée de l'étiquette (PR #53).

## Tests (dernier relevé)

| Composant | Tests automatisés | Vérifié en production (HTTP) |
|---|---|---|
| API | 370 sur `main` ; 406 avec #49 ; couverture 97 % | Catalogue, recherche, fiches, erreurs, limitation de débit |
| Web | 25 sur `main` ; 41 avec #50 | Build servi, en-têtes, relais `/api` |
| Mobile | 11 sur `main` ; 12 avec #51 | Test d'intégration HTTPS contre l'API publique : réussi |
| Bureau | 19 sur `main` ; 20 avec #51 | Test d'intégration contre l'API publique : réussi |

## Limitations connues
- **Courriels non envoyés en production** (`EMAIL_BACKEND=disabled`) : inscription et réinitialisation
  ne peuvent pas aboutir en ligne tant que Brevo n'est pas configuré.
- **Téléversement d'images** : répond 503 tant qu'aucun stockage persistant n'est activé.
- Interface d'administration **minimale** (produits) ; catégories et marques par l'API seulement.
- Politique de confidentialité en **ébauche à valider** (non définitive).
- Format d'erreur `ErrorOut` du contrat non encore appliqué (ADR-008).
- Démonstration mobile sur appareil : à réaliser ; aucun APK ni lien de build Expo publié.
- Alerte Dependabot n° 2 (`minimatch`, outillage Expo et Jest, gravité modérée) : risque toléré en
  attente d'un correctif amont, réévaluation au plus tard le 2026-12-21.

## Migrations
Head Alembic : `e2c9a4b7d3f1`. En production, Render exécute `alembic upgrade head` puis
`python -m app.seed.seed_l1 --allow-production` (idempotent) à chaque démarrage.
