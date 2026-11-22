# Preuves de tests et de CI — L1

Relevé du **21 novembre 2026**, complété le **22 novembre 2026** (production). Les résultats locaux ont été obtenus dans un environnement isolé
(PostgreSQL 16 + pgvector dédié, Python 3.11.18) ; les résultats GitHub Actions sont liés directement.

## Exécutions GitHub Actions

| PR / branche | Commit | `api-ci` | `security` | CI de l'application |
|---|---|---|---|---|
| `main` | `3d56fef` | ✅ [44848535108](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44848535108) | ✅ [44848535162](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44848535162) | — |
| #28 documents | `571d122` | ✅ [44863191630](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44863191630) | ✅ [44863191640](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44863191640) | — |
| #29 catalogue (API) | `852486c` | ✅ [44894395678](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44894395678) (tests PG16, démarrage production) | ✅ [44894395782](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44894395782) | — |
| #30 web | `9dad75c` | ✅ [44898497147](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898497147) | ✅ [44898497132](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898497132) | `web-ci` ✅ [44898497131](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898497131) |
| #31 mobile | `3564827` | ✅ [44898742749](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898742749) | ✅ [44898742762](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898742762) | `mobile-ci` ✅ [44898742756](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898742756) |
| #32 bureau | `e693e8b` | ✅ [44898504279](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898504279) | ✅ [44898504273](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898504273) | `desktop-ci` ✅ [44898504308](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898504308) (Windows) |
| #33 DevOps | `51bf338` | ✅ [44898897845](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898897845) | ✅ [44898897844](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44898897844) | — |
| `main` après #35 (courriel, IP) | `367b26f` | ✅ [44910468895](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44910468895) | ✅ [44910468943](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44910468943) | `web-ci` ✅ [44910468839](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44910468839) · `mobile-ci` ✅ [44910468835](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44910468835) · `desktop-ci` ✅ [44910468863](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44910468863) |
| `main` après #36 (Vercel → Render) | `07fc02c` | ✅ [44916468640](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44916468640) | ✅ [44916468644](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44916468644) | `web-ci` ✅ [44916468736](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44916468736) · `mobile-ci` ✅ [44916468658](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44916468658) · `desktop-ci` ✅ [44916468655](https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A/actions/runs/44916468655) |

## Résultats locaux

| Composant | Résultat | Détail |
|---|---|---|
| API (PR #29) | **329 réussis, 0 échec, 0 ignoré** ; couverture 98 % | 119 tests d'authentification existants + 210 nouveaux (schéma, stocks, entités Must, amorçage, API publique, administration) |
| API — qualité | Ruff 0.8.4, Bandit, pip-audit : conformes | |
| API — migrations | `alembic check` : aucun écart ; `downgrade base` puis `upgrade head` : conformes | |
| API — amorçage | 2 exécutions : 3 magasins, 157 produits, 471 lignes de stock, 0 doublon, 0 écart au grand livre | |
| Web (PR #30) | **21 tests réussis** ; ESLint, TypeScript, build, `npm audit` (0) : conformes | Proxy Vite vers l'API réelle vérifié |
| Mobile (PR #31) | **9 réussis, 1 ignoré** (intégration facultative) ; TypeScript ; bundle Android | Intégration contre l'API locale : **réussie** |
| Bureau (PR #32) | **19 tests réussis** ; build Release ; audit NuGet : aucun paquet vulnérable | Intégration contre l'API locale : **réussie** ; fenêtre lancée, appel `GET /api/v1/products` journalisé (200) |
| Secrets | Gitleaks 8.30.1 : aucune fuite (contenu indexé de chaque commit, historique complet) | |

## Production (tests automatisés et vérifications en ligne)

Détail et liens : [`docs/deploiement/deploiement-l1.md` §7](../deploiement/deploiement-l1.md#7-preuves-de-déploiement-artéfacts-3-6-et-7).

| Élément | Type de preuve | Résultat |
|---|---|---|
| API publique (catalogue, recherche, erreurs, HSTS) | Requêtes GET sur <https://quincaillerie-laurentienne-api.onrender.com> | 3 magasins, 157 produits, recherche FR/EN, 422/404/401 conformes |
| Limitation de débit et IP du client (F2) | 140 requêtes parallèles, en-têtes falsifiés | 120 × 200 et 20 × 429 dans les deux cas ; `CF-Connecting-IP` falsifié rejeté (403) |
| Web publié | Requêtes sur <https://quincaillerie-laurentienne-seven.vercel.app> | Build de `main`, en-têtes de sécurité, relais `/api` conforme |
| Bureau → API publique | Test d'intégration xUnit | 1 réussi |
| Mobile → API publique | Test d'intégration Jest (PR #37) | 1 réussi |

## Preuves manquantes (à compléter)

- Journal de démarrage Render (migrations jusqu'à `e2c9a4b7d3f1`, rapport d'amorçage).
- Captures d'écran du web dans un navigateur et de `/docs`.
- Démonstration du client mobile sur un appareil ou un émulateur.
- Courriels de vérification et de réinitialisation en production (fournisseur non configuré).
- Test de charge et de concurrence (prévu au L2).
