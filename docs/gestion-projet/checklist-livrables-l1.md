# Checklist des huit livrables L1 (§9.1 du cahier)

État au **22 novembre 2026** (`main` = `255e219` ; PR ouvertes #49, #50, #51). Le détail exigence par
exigence, avec les preuves et le niveau de preuve (test automatisé, HTTP, démonstration), est dans la
[matrice de traçabilité](matrice-tracabilite-l1.md).

| # | Artéfact | Statut | Reste à faire | Qui |
|---|---|---|---|---|
| 1 | Vision et exigences | PARTIEL | Validation ; lier les exigences L2/L3 à des issues | Responsable |
| 2 | Architecture (C4, ADR) | CONFORME (contenu) | Approuver les ADR « Proposé » (001 à 009) | Responsable |
| 3 | Modèle de données, migrations en production | PARTIEL | Joindre le journal Render `alembic upgrade head` (preuve P1) | Responsable |
| 4 | Modèle de menaces | CONFORME (contenu) | Validation | Responsable |
| 5 | Contrat OpenAPI | CONFORME | — | — |
| 6 | Incrément fonctionnel déployé | PARTIEL | Fusionner #49, #50, #51 ; Brevo ; comptes de démonstration ; stockage des images ; démonstration mobile ; captures | Responsable et équipe |
| 7 | DevOps | PARTIEL | Décider de l'approbation exigée (§6.1) et des contrôles obligatoires ; alerte n° 2 | Responsable |
| 8 | Gestion de projet | PARTIEL | [Tableau](https://github.com/users/MIKE08-CODE/projects/1) prêt ; sprints, responsables, heures et comptes rendus réels | Équipe |

**La L1 n'est pas encore livrable** : données de l'équipe absentes (artéfact 8), démonstrations non faites,
courriels et stockage des images inactifs en production, validations et étiquette `v0.1.0` absentes.
Liste ordonnée des décisions et procédures : [`decisions-et-validations-l1.md`](decisions-et-validations-l1.md) ;
données à fournir : [`donnees-equipe-a-completer.md`](donnees-equipe-a-completer.md).

## Ordre recommandé pour finaliser

1. Fusionner #51 (délai des clients), #50 (authentification web), #49 (téléversement), puis la PR
   documentaire de remise — chacune après mise à jour avec `main` et CI verte.
2. Configurer Brevo dans Render, puis faire le test réel (guide de déploiement §4 bis).
3. Autoriser et créer les comptes de démonstration (`procedure-comptes-demo.md`).
4. Accord sur Cloudinary (ADR-009) — ou accepter la limitation pour L1.
5. Renseigner dans le [tableau](https://github.com/users/MIKE08-CODE/projects/1) le sprint et le responsable de chaque élément (valeurs « À compléter »).
6. Remplir sprints, feuilles de temps et comptes rendus ; répéter la démonstration et remplir les grilles.
7. Faire signer le procès-verbal, puis autoriser l'étiquette `v0.1.0` et la version GitHub.
