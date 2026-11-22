# Checklist des huit livrables L1 (§9.1 du cahier)

État au **22 novembre 2026**. Légende : **local** (développé et testé localement) · **en PR** (CI GitHub
au vert, non fusionné) · **fusionné** (sur `main`) · **déployé** (URL en ligne). Les tests automatisés
réussis sont distingués des fonctionnalités **démontrées en production**.

| # | Artéfact | Exigé (§9.1) | État réel | Preuves | Reste à faire |
|---|---|---|---|---|---|
| 1 | Vision et exigences | Récits, critères, MoSCoW, liens vers les issues | **Fusionné** (#28, #34) | `docs/fondations/Vision_et_exigences_…md` | Validation du responsable ; liens des exigences L2/L3 |
| 2 | Architecture | C4 niveaux 1-2, choix, ≥ 3 ADR | **Fusionné** : C4, ADR 001 à 003 et 0004 à 0008 | `docs/architecture/`, `docs/adr/` | Approbation des ADR « Proposé » ; hébergement réel dans le diagramme de déploiement |
| 3 | Modèle de données | ER des entités Must, dictionnaire, migrations **appliquées en production** | **Fusionné et déployé** : la production sert les données et la recherche qui dépendent des migrations | [Preuves](preuves-tests-ci.md), `docs/deploiement/deploiement-l1.md` §7 | Joindre le journal Render de `alembic upgrade head` |
| 4 | Modèle de menaces | STRIDE paiement/cueillette, frontières, mesures | **Fusionné** | `docs/fondations/modele-de-menaces_…md` | Validation |
| 5 | Contrat d'API | OpenAPI généré, routes implémentées et prévues | **Fusionné** ; `/openapi.json` en ligne | `docs/api/openapi-l1.json` | Régénérer après les prochains changements d'API |
| 6 | Incrément fonctionnel | L1 **déployé** ; trois clients connectés à l'API **en ligne** | **Déployé** : API et web en ligne ; bureau testé contre l'API publique ; mobile testé contre l'API publique (PR #37) ; images de remplacement (PR #39) ; comptes de démonstration (PR #38, non créés en production) | `docs/deploiement/deploiement-l1.md` §7 | Démonstration mobile sur appareil ; fournisseur de courriel (A-AUTH-01, A-AUTH-04) ; téléversement d'images (A-ADM-01) ; création des comptes de démonstration (autorisation) |
| 7 | DevOps | Protection de branche, CI verte pour chaque application, déploiement automatique, Dependabot/CodeQL/secrets, README | Protection de `main` **active** ; 5 workflows **fusionnés et verts** ; déploiement automatique Render et Vercel **actif** ; README à jour ; CodeQL JS/TS et C#, Dependabot npm/NuGet **en PR** #40 | [Preuves](preuves-tests-ci.md) | Fusion de #40 ; alerte Dependabot n° 2 (sans correctif amont) ; décision sur l'approbation exigée (§6.1) et les contrôles obligatoires |
| 8 | Gestion de projet | GitHub Projects, rapports S1-S3, feuilles de temps, comptes rendus, risques | Registre des risques et gabarits **fusionnés** ; feuilles de temps, comptes rendus, rapports de sprint et tableau **à compléter** | Ce dossier | Données réelles de l'équipe ; tableau GitHub Projects |

**La L1 n'est pas encore livrée** : la gestion de projet est incomplète, la démonstration mobile n'est pas
faite, le courriel n'est pas configuré en production et l'étiquette `v0.1.0` n'existe pas.

## Autorisations et actions nécessaires pour finaliser

1. Fusionner les PR #37 à #41 (le ruleset `strict` exige de mettre chaque branche à jour avec `main`).
2. Décisions : fournisseur de courriel (Brevo), création des comptes de démonstration en production,
   fermeture de l'alerte Dependabot n° 2, contrôles CI obligatoires, approbation exigée.
3. Droit `project` pour le jeton `gh` (`gh auth refresh -s project`) afin de créer le tableau.
4. Création de l'étiquette `v0.1.0` et de la version GitHub (notes de version).
