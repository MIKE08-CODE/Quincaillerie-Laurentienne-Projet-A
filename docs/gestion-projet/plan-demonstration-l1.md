# Plan de démonstration L1 — 20 minutes + questions

**Préalables (la veille)** : PR fusionnées, API et web déployés (sinon : plan de repli local, voir à la
fin), API réveillée 10 minutes avant, base amorcée (`GET /api/v1/products?size=1` → `total` 157),
appareil mobile avec Expo Go ou émulateur prêt, application de bureau compilée pointant vers l'URL
publique, comptes de démonstration créés **hors du dépôt** (identifiants transmis en privé).

| Min. | Séquence | Présentateur | Ce qu'on montre | Preuve |
|---|---|---|---|---|
| 0–2 | Contexte et vision | À compléter | Problèmes de la quincaillerie, objectifs, périmètre L1 | Vision et exigences |
| 2–5 | Architecture | À compléter | C4 niveaux 1-2, choix, ADR (verrouillage, jetons, Expo, marques, grand livre, recherche) | `docs/architecture/`, `docs/adr/` |
| 5–7 | Données et sécurité | À compléter | Entités Must et migrations ; STRIDE paiement/cueillette ; mesures déjà en place | Modèle de données §8, modèle de menaces §8 |
| 7–13 | **Démonstration web** | À compléter | Accueil → catégorie « Perceuses » → tri par prix → fiche « Perceuse-visseuse 18 V » (disponibilité par magasin) → recherche « drill », puis « equerre » → bascule FR/EN | URL du web |
| 13–15 | **Mobile et bureau** | À compléter | Mobile : liste et filtre par catégorie ; bureau : liste et recherche ; même API en ligne | Appareil ; fenêtre Windows |
| 15–17 | API et administration | À compléter | `/docs` (OpenAPI) ; `/admin/products` sans jeton → 401 ; client → 403 ; administrateur avec MFA → PATCH d'un prix visible sur le web | OpenAPI ; tests `test_admin_catalog` |
| 17–19 | DevOps | À compléter | Ruleset de `main`, PR avec CI verte (5 workflows), Dependabot, CodeQL, Gitleaks, déploiement automatique | GitHub Actions ; [preuves](preuves-tests-ci.md) |
| 19–20 | Bilan et suite | À compléter | Livrables, limites (courriel, ErrorOut, images), plan L2 | Checklist |

## Questions probables et réponses préparées

| Question | Réponse et preuve |
|---|---|
| Comment évitez-vous la survente ? | Au L1 : contraintes `0 ≤ reserved ≤ on_hand`, grand livre en ajout seulement, verrou `FOR UPDATE` (ADR-001, ADR-005). Test de 50 acheteurs sur 5 unités : prévu au L2 avec les réservations. |
| Pourquoi une table `brands` alors que A.6 parle d'un attribut ? | A-ADM-01 exige un CRUD des marques ; A.6 permet d'ajouter des entités (ADR-004). |
| Comment la recherche ignore-t-elle les accents ? | Configurations `fr_unaccent`/`en_unaccent`, colonne `search_vector` générée et index GIN (ADR-006) ; tests « perceuse », « drill », « equerre ». |
| Le stock est-il visible par le public ? | Non : seul un statut calculé (En stock, Stock faible, Rupture) est renvoyé ; un test vérifie l'absence de quantités. |
| Qui peut modifier le catalogue ? | L'administrateur ayant complété la MFA ; matrice testée sur les 15 routes pour chaque rôle. |
| Pourquoi React 19 sur le mobile ? | Expo SDK 58 l'impose ; le web reste en React 18 (ADR-007). |
| Où sont les secrets ? | Variables d'environnement de l'hébergeur ; aucun secret dans Git (Gitleaks, secret scanning, push protection). |
| Qu'est-ce qui n'est pas fait ? | Envoi de courriels en production, format `ErrorOut`, téléversement d'images, interface web d'administration ; fonctions transactionnelles et RAG au L2. |

## Plan de repli (si l'hébergement n'est pas disponible)

Démonstration locale : base PostgreSQL 16 + amorçage, API `uvicorn`, web `npm run dev`, mobile
`npx expo start`, bureau `dotnet run`. **Le dire explicitement** : l'artéfact 6 exige un déploiement en
ligne, et la démonstration locale ne le remplace pas.
