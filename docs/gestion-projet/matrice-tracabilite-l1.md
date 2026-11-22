# Matrice de traçabilité et de conformité — L1 (v0.1.0)

Relevé du **22 novembre 2026**, sur `main` = `255e219`, avec les PR ouvertes #49, #50 et #51 (CI à vérifier
avant fusion). Sources : cahier des charges §6.1, §6.2, §6.3, §8, §9.1 et A.11 ; historique Git et GitHub ;
vérifications HTTP en lecture seule de la production.

**Trois niveaux de preuve, jamais confondus :**

| Sigle | Signification |
|---|---|
| **TA** | Test automatisé réussi (pytest, Vitest, Jest, xUnit), en local et/ou en CI GitHub |
| **HTTP** | Vérification par requêtes réelles contre la production (GET/OPTIONS seulement, aucune donnée modifiée) |
| **DÉMO** | Démonstration visuelle réelle (navigateur, appareil, fenêtre) observée par une personne |

Statuts : **CONFORME** · **PARTIEL** · **MANQUANT** · **NON VÉRIFIABLE** (preuve hors de portée de l'outillage).

## 1. Portée fonctionnelle A.11 (« déployée et démontrable »)

| Exigence | Livrable attendu | Issue | PR | Preuve existante | Écart | Priorité | Correction | Statut |
|---|---|---|---|---|---|---|---|---|
| A-AUTH-01 Inscription | Inscription, vérification du courriel | #1 (fermée) | #21, #35, **#50** | TA : `test_register.py`, `test_email_delivery.py` ; web : `Auth.test.tsx` (#50) | **Aucun courriel envoyé en production** (`EMAIL_BACKEND=disabled`) ; pages web dans #50 (non fusionnée) ; pas de page de politique de confidentialité | P1 | Fusionner #50 ; configurer Brevo (§D1 du guide de déploiement) ; test réel avec une adresse du responsable | PARTIEL |
| A-AUTH-02 Connexion et jetons | Jeton d'accès 15 min, cookie httpOnly, rotation | #2 (fermée) | #21, **#50** | TA : `test_tokens.py` ; HTTP : 401 sans jeton | Pas encore démontré dans le web en production (#50) | P1 | Fusionner #50 ; démonstration avec un compte de démonstration | PARTIEL |
| A-AUTH-03 Politique et hachage | ≥ 12 caractères, liste commune, Argon2id | #3 (fermée) | #21 | TA : `test_password_policy.py` | — | — | — | CONFORME |
| A-AUTH-04 Réinitialisation | Lien 30 min, usage unique, réponse neutre | #4 (fermée) | #21, #35, **#50** | TA : `test_password_reset.py` ; web : `Auth.test.tsx` (#50) | Même blocage courriel que A-AUTH-01 | P1 | Idem A-AUTH-01 | PARTIEL |
| A-AUTH-05 Rôles | Client, commis, gérant, administrateur | #5 (fermée) | #21, #38 | TA : `test_rbac.py`, matrice des rôles de `test_admin_catalog.py`, `test_demo_accounts.py` | Comptes de démonstration non créés en production | P1 | Autoriser la création (procédure `procedure-comptes-demo.md`) | CONFORME (code) / à démontrer |
| A-AUTH-07 Débit et verrouillage | Limitation par IP, verrouillage progressif | #6 (ouverte) | #21, #35 | TA : `test_lockout.py`, `test_client_ip.py` ; HTTP : 140 requêtes → 120 × 200 et 20 × 429, IP falsifiée sans effet | Issue #6 encore ouverte | P2 | Fermer #6 (décision du responsable) | CONFORME |
| A-AUTH-06 MFA (hors liste A.11, exigée pour le personnel) | TOTP pour le personnel | — | #21, #38 | TA : `test_mfa.py`, `test_demo_accounts.py` | — | — | — | CONFORME (code) |
| A-CAT-01 Liste et catégories | Liste paginée, catégories | #7 (ouverte) | #29, #30 | TA ; HTTP : 157 produits, 7 catégories racines, `size=51` → 422 | Issue #7 ouverte | P2 | Fermer #7 | CONFORME |
| A-CAT-02 Fiche et disponibilité | Fiche bilingue, statut par magasin sans quantité | #8 (ouverte) | #29, #30, #39 | TA ; HTTP : fiche `PERC-18V`, 3 statuts, aucune quantité | Issue #8 ouverte | P2 | Fermer #8 | CONFORME |
| A-CAT-03 Recherche FR/EN | Plein texte, insensible aux accents | #9 (ouverte) | #29, #30 | TA ; HTTP : `perceuse` 13, `drill` 14, `equerre`/`équerre` 5 | Issue #9 ouverte | P2 | Fermer #9 | CONFORME |
| A-ADM-01 Gestion des produits | CRUD produits, catégories, marques ; **téléversement d'images validé (type, taille)** | #10 (ouverte), #17 | #29, **#49** | TA : `test_admin_catalog.py` ; `test_image_upload.py` (#49) | Stockage persistant **non activé** (503 en production) ; **aucune interface web d'administration** | P1 | Fusionner #49 ; accord sur Cloudinary (ADR-009) ; décider de l'interface | PARTIEL |
| Données d'amorçage | 3 magasins, ≥ 150 produits, stocks | — | #29 | TA : `test_seed_l1.py` ; HTTP : 3 magasins, 157 produits | — | — | — | CONFORME |
| Catalogue web et fiche déployés | URL publique | — | #30, #36, #39 | HTTP : <https://quincaillerie-laurentienne-seven.vercel.app>, build de `main`, relais `/api`, en-têtes de sécurité | Aucune capture d'écran ; vérification visuelle non faite par l'outillage | P1 | Captures (liste en §4) | CONFORME (HTTP) / DÉMO à faire |
| Bureau connecté à l'API en ligne | Liste des produits | — | #32, **#51** | TA : intégration contre l'API publique réussie | Aucune capture de la fenêtre connectée à l'API publique | P1 | Capture (§4) | CONFORME (TA) / DÉMO à faire |
| Mobile connecté à l'API en ligne | Liste des produits | — | #31, #37, **#51** | TA : intégration HTTPS contre l'API publique réussie | **Aucune démonstration sur appareil ou émulateur** ; délai de 10 s trop court au réveil de Render (corrigé dans #51) | **P0** | Fusionner #51 ; démonstration (`plan-demonstration-l1.md` §3) | PARTIEL |

## 2. Artéfacts §9.1

| # | Artéfact | Preuve | Écart | Priorité | Statut |
|---|---|---|---|---|---|
| 1 | Vision et exigences | `docs/fondations/Vision_et_exigences_Quincaillerie_Laurentienne.md` (49 récits, critères, MoSCoW, liens #1 à #10) | Validation du responsable en attente ; exigences L2/L3 non reliées à des issues | P2 | PARTIEL |
| 2 | Architecture (C4 1-2, ≥ 3 ADR) | `docs/architecture/architecture_Quincaillerie_Laurentienne.md` (4 diagrammes), ADR 001 à 003, `docs/adr/0004` à `0009` | ADR au statut « Proposé » (approbation humaine requise) | P2 | CONFORME (contenu) |
| 3 | Modèle de données, migrations en production | `docs/fondations/modele-de-donnees_…md` ; `api/alembic/versions/` ; HTTP : données et recherche servies (dépendent des migrations) | **Journal Render `alembic upgrade head` non joint** | P1 | PARTIEL |
| 4 | Modèle de menaces STRIDE | `docs/fondations/modele-de-menaces_…md` | Validation en attente | P3 | CONFORME (contenu) |
| 5 | Contrat OpenAPI | `docs/api/openapi-l1.json` (28 chemins avec #49) ; `/openapi.json` en ligne | — | — | CONFORME |
| 6 | Incrément fonctionnel | Section 1 | Courriel, images, démonstration mobile | P0/P1 | PARTIEL |
| 7 | DevOps | Ruleset `protect-main` ; 5 workflows verts sur `main` ; déploiements Render et Vercel automatiques ; CodeQL (Python, actions, JS/TS, C#) ; Dependabot (pip, npm, NuGet, actions) ; Gitleaks ; secret scanning ; README | **§6.1 : 0 approbation exigée au lieu d'1** ; contrôles `web-ci`, `mobile-ci`, `desktop-ci` non obligatoires ; alerte Dependabot n° 2 ouverte (risque R14) | P2 | PARTIEL (écart §6.1 assumé, à valider) |
| 8 | Gestion de projet | `docs/gestion-projet/` ; [tableau GitHub Projects n° 1](https://github.com/users/MIKE08-CODE/projects/1) (60 éléments : issues, PR fusionnées, éléments L1 ; champs Sprint, Priorité, Jalon, Exigence, PR fusionnées, Responsable, Heures, Preuve) | Structure prête ; **sprints, responsables, heures, comptes rendus et rétrospectives sans données de l'équipe** (valeur « À compléter ») | **P0** | PARTIEL |

## 3. Règles transversales

| Règle | Exigence | Preuve | Écart | Statut |
|---|---|---|---|---|
| §6.1 `main` protégée | Aucune poussée directe, ≥ 1 approbation, CI verte | Ruleset : PR obligatoire, squash, `api-ci` et `security` obligatoires, fils résolus | 0 approbation (un seul développeur) | PARTIEL |
| §6.1 Nommage des branches | `feature/<issue>-…`, `fix/<issue>-…`, `docs/…` | Historique des PR | Plusieurs branches sans numéro d'issue (`feature/l1-web`, …) | PARTIEL |
| §6.1 Conventional Commits | `feat:`, `fix:`, `docs:` … | `git log` | — | CONFORME |
| §6.1 PR liée à une issue, gabarit, < 400 lignes | Gabarit quoi/pourquoi/tests/sécurité | Corps des PR | 9 des 11 premières PR > 400 lignes (lockfiles inclus) ; quelques références d'issue approximatives (#38 → « Refs #6 ») | PARTIEL |
| §6.1 / §8 Version étiquetée `v0.1.0` + notes | Étiquette, version GitHub, notes, URL | `notes-de-version-v0.1.0.md` (brouillon prêt) | **Étiquette et version non créées** (autorisation requise) | MANQUANT |
| §6.3 `.env` non versionné, `.env.example` versionné | | `.gitignore`, `.env.example` | — | CONFORME |
| §6.3 Secrets dans le tableau de bord | | Render, Vercel ; Gitleaks : 0 fuite | — | CONFORME |
| §6.3 Comptes de démonstration par rôle, identifiants en privé | Script d'amorçage | `app.seed.demo_accounts` (#38), `procedure-comptes-demo.md` | Non exécuté en production | PARTIEL |
| §6.3 Bureau distribué par GitHub Releases ; mobile en APK ou lien Expo | | Workflow `desktop-release` : paquet Windows autonome (ZIP + SHA-256) joint à une version **en brouillon** à la création de l'étiquette | Bureau : prêt, publié seulement après l'étiquette et votre relecture ; mobile : aucun APK ni lien Expo (compte Expo requis) | PARTIEL |
| §6.3 Offres gratuites uniquement | | Neon, Render, Vercel gratuits ; aucune carte | — | CONFORME |
| §8 Démonstration de 20 min + questions | Scénario | `plan-demonstration-l1.md` | Répétition à faire | PARTIEL |

## 4. Preuves à fournir manuellement (aucune ne peut être produite par l'outillage)

| # | Preuve | Où l'obtenir | Pour |
|---|---|---|---|
| P1 | Journal de démarrage Render : `alembic upgrade head` jusqu'à `e2c9a4b7d3f1` et rapport d'amorçage | Render → service → Logs (copier sans aucun secret) | Artéfact 3 |
| P2 | Capture du site : catalogue, recherche « drill », fiche `PERC-18V` avec disponibilités et image de remplacement | Navigateur sur l'URL Vercel | A.11 web |
| P3 | Capture de `/docs` de l'API | <https://quincaillerie-laurentienne-api.onrender.com/docs> | Artéfact 5 |
| P4 | Vidéo ou captures du mobile (liste, recherche, fiche) connecté à l'API publique | Expo Go ou émulateur Android | A.11 mobile |
| P5 | Capture de la fenêtre de bureau connectée à l'API publique | Windows | A.11 bureau |
| P6 | Courriel de vérification reçu et lien ouvert jusqu'à « adresse vérifiée » ; idem réinitialisation | Après configuration Brevo | A-AUTH-01, A-AUTH-04 |
| P7 | Tableau GitHub Projects rempli par l'équipe (sprints, responsables, heures), puis capture | https://github.com/users/MIKE08-CODE/projects/1 | Artéfact 8 |
| P8 | Feuilles de temps, comptes rendus, rapports de sprint remplis | Équipe | Artéfact 8 |
| P9 | Procès-verbal d'approbation signé | `proces-verbal-approbation-l1.md` | Remise |
