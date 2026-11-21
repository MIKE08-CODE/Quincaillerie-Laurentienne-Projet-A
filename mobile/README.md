# mobile — Application mobile

Application mobile client bilingue (langue de l'appareil, français par défaut) de Quincaillerie
Laurentienne. Au L1, elle se connecte à l'API et affiche la liste des produits, avec navigation par
catégorie (A-CAT-01 : « navigation par catégorie fonctionnelle sur le web et le mobile »).

**Stack :** React Native 0.88 + Expo SDK 58 (React 19.3), TypeScript ; tests Jest (`jest-expo`) et
React Native Testing Library.

> **Écart à consigner (ADR-003)** : Expo SDK 58 impose React 19, alors que l'application web reste sur
> React 18 comme l'exige le cahier. Les deux applications ne partagent pas de code React; seul le
> contrat de l'API est commun.

## Fonctionnalités L1

| Élément | Détail |
|---|---|
| Liste des produits | `GET /products` (20 par page, tri par nom), bouton « Charger plus », rafraîchissement par glissement |
| Catégories | Puces des catégories de premier niveau (`GET /categories`), filtre `category_id` (sous-catégories incluses par l'API) |
| États | Indicateur de chargement, message d'erreur (réseau ou API) avec « Réessayer », liste vide |
| Prix | Cents → dollars canadiens localisés (`19,99 $` / `$19.99`) |

## Configuration de l'URL de l'API par environnement

L'URL est lue dans `EXPO_PUBLIC_API_BASE_URL` au moment du bundle (préfixe `/api/v1` inclus). Copier
`.env.example` en `.env.development` (utilisé par `expo start`) et `.env.production` (build de
production). Ces fichiers ne sont pas versionnés.

| Cible | Valeur |
|---|---|
| Émulateur Android | `http://10.0.2.2:8000/api/v1` |
| Appareil réel (même Wi-Fi) | `http://<IP-du-poste>:8000/api/v1` (lancer l'API avec `--host 0.0.0.0`) |
| API déployée | `https://<hôte-de-l-api>/api/v1` — **à compléter après le déploiement** |

Défaut sans configuration : `http://localhost:8000/api/v1`. Les variables `EXPO_PUBLIC_*` sont publiques :
n'y mettez jamais de secret.

## Lancer

```bash
cd mobile
npm ci
cp .env.example .env.development   # puis ajuster EXPO_PUBLIC_API_BASE_URL
npx expo start                     # QR code pour Expo Go, ou touche « a » pour l'émulateur Android
```

## Contrôles

```bash
npm run typecheck                                   # TypeScript
npm test                                            # Jest (fetch simulé)
API_INTEGRATION_URL=http://localhost:8000/api/v1 npm test -- api.integration   # contre une API réelle
npx expo export --platform android --output-dir /tmp/expo-export               # bundle de production
```

Le workflow `mobile-ci` exécute les types, les tests, le bundle Android et `npm audit --audit-level=high`.

**Exception d'audit documentée** (2026-11-21) : 3 vulnérabilités modérées (`glob`
GHSA-3g3m-2fjr-6pw4, `minimatch` GHSA-g3hv-75wg-m249) dans l'outillage en ligne de commande d'Expo et
de Jest, qui n'est pas embarqué dans l'application installée. La seule correction proposée par npm est
une rétrogradation vers Expo 52 : à réévaluer à chaque mise à jour d'Expo.

**Non vérifié dans ce dépôt** : exécution sur un appareil ou un émulateur (aucun émulateur dans
l'environnement de développement utilisé) ; la compilation du bundle Android et l'appel de l'API réelle
par le client HTTP de l'application sont, eux, vérifiés.

| Dossier | Rôle |
|---|---|
| `src/api/` | Client HTTP (délai maximal de 10 s) et appels du catalogue |
| `src/config.ts` | URL de l'API par environnement |
| `src/i18n/` | Textes FR/EN et formatage des prix |
| `src/screens/` | Écrans |
| `src/__tests__/` | Tests |
| `assets/` | Icônes, splash |
