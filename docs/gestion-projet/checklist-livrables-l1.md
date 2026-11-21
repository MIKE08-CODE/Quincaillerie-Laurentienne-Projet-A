# Checklist des huit livrables L1 (§9.1 du cahier)

État au **21 novembre 2026**. Légende : **local** (développé et testé localement) · **poussé** · **en PR**
(CI GitHub au vert, non fusionné) · **fusionné** (sur `main`) · **déployé** (URL en ligne).

| # | Artéfact | Exigé (§9.1) | État réel | Preuves | Reste à faire |
|---|---|---|---|---|---|
| 1 | Vision et exigences | Récits, critères, MoSCoW, liens vers les issues | **En PR** #28 (v1.2) ; mise à jour v1.3 (liens #1 à #10, état L1) dans la PR documentaire de suivi | `docs/fondations/Vision_et_exigences_…md` | Fusion ; validation du responsable ; liens des exigences L2/L3 |
| 2 | Architecture | C4 niveaux 1-2, choix, ≥ 3 ADR | **En PR** #28 (C4 + ADR 001 à 003) ; ADR 004 à 008 et état réel dans la PR de suivi | `docs/architecture/`, `docs/adr/` | Fusion ; approbation des ADR « Proposé » |
| 3 | Modèle de données | ER des entités Must, dictionnaire, migrations **appliquées en production** | Document **en PR** #28 + §8 (schéma vérifié) ; migrations **en PR** #29 | `alembic check`, aller-retour testé, 329 tests | Fusion #29 ; **déploiement** et preuve en production |
| 4 | Modèle de menaces | STRIDE paiement/cueillette, frontières, mesures | **En PR** #28 ; §8 « état des mesures au L1 » dans la PR de suivi | `docs/fondations/modele-de-menaces_…md` | Fusion ; validation |
| 5 | Contrat d'API | OpenAPI généré, routes implémentées et prévues | **En PR** #28 + §18 (conformité) et `docs/api/openapi-l1.json` dans la PR de suivi | OpenAPI généré au commit `852486c` (34 opérations) | Fusion ; régénérer après le sous-lot 0.A |
| 6 | Incrément fonctionnel | L1 **déployé** ; trois clients connectés à l'API **en ligne** | API **en PR** #29 ; web #30 ; mobile #31 ; bureau #32 ; clients testés contre l'API **locale** | Tests d'intégration mobile et bureau ; démonstration HTTP | Fusions ; **déploiement** ; tests contre l'URL publique |
| 7 | DevOps | Protection de branche, CI verte pour chaque application, déploiement automatique, Dependabot/CodeQL/secrets, README | Protection de `main` **active** ; `api-ci`, `security` **fusionnés** ; `web-ci`, `mobile-ci`, `desktop-ci` **en PR** (verts) ; README et déploiement préparé **en PR** #33 ; Dependabot/CodeQL clients **local** (`ci/l1-securite-clients`) | Exécutions GitHub Actions ([preuves](preuves-tests-ci.md)) | Fusions ; ouvrir la PR Dependabot/CodeQL clients après #30 à #32 ; activer le déploiement (Render, Vercel, Neon) |
| 8 | Gestion de projet | GitHub Projects, rapports S1-S3, feuilles de temps, comptes rendus, risques | **Local** (ce dossier) ; registre des risques et preuves rédigés ; feuilles de temps, comptes rendus et tableau **à compléter** | Ce dossier | Données réelles de l'équipe ; tableau GitHub Projects |

**La L1 n'est pas livrée** : aucune PR de cette série n'est fusionnée, rien n'est déployé, l'étiquette
`v0.1.0` n'existe pas.

## Autorisations nécessaires pour finaliser

1. Fusionner, dans l'ordre : #28 → PR documentaire de suivi → #29 → #30, #31, #32 → #33 → PR
   Dependabot/CodeQL clients (le ruleset `strict` exige de mettre chaque branche à jour avec `main`).
2. Décisions : fournisseur de courriel, hébergement (Neon, Render, Vercel), contrôles CI obligatoires,
   exceptions d'audit mobile, ADR-007.
3. Création des comptes et des secrets d'hébergement, puis déploiement.
4. Droit `project` pour le jeton `gh` (`gh auth refresh -s project`) afin de créer le tableau.
5. Création de l'étiquette `v0.1.0` et de la version GitHub (notes de version).
