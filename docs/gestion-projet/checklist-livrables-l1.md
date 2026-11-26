# Checklist des huit livrables L1 (§9.1 du cahier)

État au **26 novembre 2026** (`main` = `a8d88cf`, seule PR ouverte : Dependabot #42). Détail exigence
par exigence : [matrice de traçabilité](matrice-tracabilite-l1.md) ; niveau de chaque preuve :
[registre des preuves](registre-preuves-l1.md) ; étapes restantes : [recette finale](recette-finale-l1.md).

| # | Artéfact (§9.1) | Statut | Preuves | Reste à faire |
|---|---|---|---|---|
| 1 | Vision et exigences | CONFORME (contenu) | 33 récits « En tant que… », critères, MoSCoW, liens vers les issues | Approbation au procès-verbal |
| 2 | Architecture (C4 1–2, ≥ 3 ADR) | CONFORME (contenu) | Diagrammes de contexte et de conteneurs ; 9 ADR | Statuer sur les ADR « Proposé » (001 à 003, 007, 009) |
| 3 | Modèle de données, dictionnaire, migrations en production | CONFORME | 3 diagrammes ER, dictionnaire ; 5 migrations ; démarrage Render `alembic upgrade head && …` réussi sur `a8d88cf` (P1) | Capture du journal (complément) |
| 4 | Modèle de menaces STRIDE (paiement, cueillette) | CONFORME (contenu) | Flux paiement et cueillette, frontières de confiance, mesures reliées à 18 exigences | Approbation au procès-verbal |
| 5 | Contrat OpenAPI | CONFORME | `docs/api/openapi-l1.json` identique à la production (28 chemins, 35 schémas) ; routes prévues documentées | — |
| 6 | Incrément fonctionnel déployé, trois clients connectés | PARTIEL | Catalogue, fiche, recherche, authentification, administration et images en production ; mobile et bureau : tests d'intégration contre l'API en ligne | **A-AUTH-01 à tester en réel** (P6) ; démonstrations W, M, B ; issue #7 (M3) |
| 7 | DevOps | PARTIEL | Ruleset de `main` (PR, CI obligatoire, squash) ; 5 workflows verts ; déploiement automatique ; Dependabot, CodeQL, Gitleaks, secret scanning ; README d'installation ; gabarit de PR (§6.1) | **§6.1 : une approbation exigée** (0 aujourd'hui, un seul collaborateur) ; alerte Dependabot n° 2 |
| 8 | Gestion de projet | PARTIEL | Tableau (70 éléments) ; registre des risques ; gabarits de rapports, feuilles de temps et comptes rendus | **Données réelles de l'équipe** : sprints, heures, réunions, rétrospectives (P8) |

Hors artéfacts : version étiquetée `v0.1.0` avec notes (§6.1, §8) — **après autorisation écrite** ;
procès-verbal signé (P9).

**La L1 n'est pas encore livrable** : A-AUTH-01 non testé en réel, démonstrations et captures à faire,
données de l'équipe absentes, écart §6.1, validations et étiquette à venir.
