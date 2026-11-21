# web — Application web

Interface web bilingue (FR par défaut, EN), adaptée au mobile, du catalogue L1 de Quincaillerie
Laurentienne. Elle consomme uniquement l'API REST `/api/v1` (aucun accès direct à la base).

**Stack :** React 18, Vite 6, TypeScript, React Router 7, i18next ; tests Vitest + Testing Library.

## Fonctionnalités L1

| Page | Route | Exigence | API utilisée |
|---|---|---|---|
| Accueil (catégories, nouveautés) | `/` | A-CAT-01 | `GET /categories`, `GET /products?sort=newest` |
| Catalogue (arbre de catégories, tri, pagination de 24) | `/produits?categorie=&tri=&page=` | A-CAT-01 | `GET /categories`, `GET /products` |
| Recherche FR/EN, sans accents | `/recherche?q=` | A-CAT-03 | `GET /search` |
| Fiche produit et disponibilité par magasin | `/produits/:id` | A-CAT-02 | `GET /products/{id}` |
| Magasins et heures | `/magasins` | A.8.1 | `GET /stores` |

Chaque appel affiche un état de chargement, un message d'erreur (avec « Réessayer ») ou un message
d'absence de résultats. La langue choisie est mémorisée dans le navigateur ; les prix sont formatés en
dollars canadiens selon la langue (`129,99 $` / `$129.99`).

## Lancer en local

Prérequis : Node.js 20 ou plus, et l'API lancée sur `http://localhost:8000` (voir `api/README.md`),
avec la base migrée et amorcée (`alembic upgrade head`, puis `python -m app.seed.seed_l1`).

```bash
cd web
npm ci                       # installation exacte selon package-lock.json
cp .env.example .env.local   # facultatif : les valeurs par défaut conviennent en local
npm run dev                  # http://localhost:5173
```

En développement, Vite relaie `/api` vers `VITE_API_PROXY_TARGET` (par défaut `http://localhost:8000`) :
le navigateur reste sur la même origine.

## Contrôles

```bash
npm run lint        # ESLint
npm run typecheck   # TypeScript
npm test            # Vitest (fetch simulé)
npm run build       # build de production dans dist/
```

Les mêmes contrôles, plus `npm audit`, sont exécutés par le workflow `web-ci`.

## Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Préfixe des appels à l'API (même origine) |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Développement : adresse de l'API relayée par Vite |

Les variables `VITE_*` sont publiques (incluses dans le JavaScript livré) : n'y mettez jamais de secret.

| Dossier | Rôle |
|---|---|
| `src/api/` | Client HTTP et appels du catalogue |
| `src/components/` | Composants UI réutilisables |
| `src/hooks/` | `useApi` (requête annulable), `useReload` |
| `src/i18n/` | Traductions FR/EN et formatage |
| `src/layouts/` | Gabarit (en-tête, recherche, langue) |
| `src/pages/` | Pages |
| `src/routes/` | Définition des routes |
| `src/test/` | Configuration et utilitaires de test |
