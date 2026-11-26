# Plan de démonstration L1 — 20 minutes + questions (cahier §8)

> Procédures pas à pas des grilles W, M et B : [`recette-finale-l1.md`](recette-finale-l1.md).

**Rien dans ce plan n'a encore été répété.** Chaque séquence indique le niveau de preuve disponible
aujourd'hui (TA : test automatisé ; HTTP : vérifié en production par requêtes ; DÉMO : à montrer en
direct, jamais réalisé par l'outillage).

## 1. Préparation (la veille et 15 minutes avant)

| # | Action | Vérification attendue |
|---|---|---|
| 1 | Fusions retenues faites, déploiements Render et Vercel « Live » sur le dernier commit de `main` | Statuts verts sur le commit GitHub |
| 2 | **Réveiller l'API 15 minutes avant** : ouvrir `https://quincaillerie-laurentienne-api.onrender.com/health` | `{"status":"ok"}` (jusqu'à une minute au réveil) |
| 3 | `GET /api/v1/products?size=1` | `"total": 157` |
| 4 | Comptes de démonstration créés **avec autorisation** (`procedure-comptes-demo.md`), MFA du compte administrateur configurée sur un téléphone | Connexion réussie de chaque compte |
| 5 | Mobile prêt (section 3) | Liste des produits affichée |
| 6 | Bureau compilé, `QL_API_BASE_URL=https://quincaillerie-laurentienne-api.onrender.com/api/v1` | Liste des produits affichée |
| 7 | Onglets ouverts : site, `/docs`, dépôt GitHub (Actions, ruleset), tableau Projects | — |

## 2. Déroulé

| Min. | Séquence | Présentateur | Ce qu'on montre | Preuve aujourd'hui |
|---|---|---|---|---|
| 0–2 | Contexte et vision | À désigner | Problème, objectifs, périmètre L1 | Document de vision |
| 2–5 | Architecture | À désigner | C4 niveaux 1-2 ; ADR (verrouillage, jetons, Expo, marques, grand livre, recherche, erreurs, images) | `docs/architecture/`, `docs/adr/` |
| 5–7 | Données et sécurité | À désigner | Entités Must et migrations ; STRIDE paiement/cueillette ; mesures en place | Modèle de données, modèle de menaces |
| 7–12 | **Web** | À désigner | Catégorie « Perceuses » → tri par prix → fiche `PERC-18V` (disponibilité par magasin, image de remplacement) → recherche « drill » puis « equerre » → bascule FR/EN | HTTP ✔ ; DÉMO à faire |
| 12–14 | **Authentification web** | À désigner | Connexion du compte client → « Mon compte » → déconnexion ; mauvais mot de passe → message neutre ; mot de passe oublié → courriel Brevo reçu | TA ✔ (#50) ; réinitialisation réelle ✔ (déclarée) ; vérification à l'inscription à tester (P6) |
| 14–16 | **Mobile et bureau** | À désigner | Mobile : liste, catégorie ; bureau : liste et recherche ; même API en ligne | TA d'intégration ✔ ; DÉMO à faire |
| 16–18 | Administration | À désigner | Connexion du compte administrateur (code MFA) → `/admin` → modifier le prix de `PERC-18V`, visible sur la fiche du site → téléverser une image, qui devient l'image principale de la carte et de la fiche ; `/docs` : `/api/v1/admin/products` sans jeton → 401, client → 403 | TA ✔ (#55, #64) ; C1 à C8 ✔ (déclarés) ; DÉMO à répéter |
| 18–19 | DevOps | À désigner | Ruleset de `main`, PR avec CI verte, CodeQL (4 langages), Dependabot, Gitleaks, déploiement automatique | GitHub ✔ |
| 19–20 | Bilan | À désigner | Huit artéfacts, limites assumées, plan L2 | Matrice de traçabilité |

## 3. Procédure de démonstration mobile (Android)

**Option A — Expo Go sur un téléphone Android (recommandée, gratuite)**
1. Installer **Expo Go** depuis Google Play ; vérifier qu'il prend en charge le **SDK 58** (sinon option B).
2. Sur le poste : `cd mobile && npm ci`.
3. Créer `mobile/.env.production` (non versionné) :
   `EXPO_PUBLIC_API_BASE_URL=https://quincaillerie-laurentienne-api.onrender.com/api/v1`.
4. `npx expo start --tunnel` (le tunnel évite les problèmes de réseau Wi-Fi), puis scanner le code QR.
5. Réveiller l'API (§1, étape 2) avant d'ouvrir l'application.

**Option B — Émulateur Android (Android Studio, gratuit)** : créer un appareil virtuel récent, puis
`npx expo start` et touche `a`. L'URL publique de l'API reste la même (HTTPS).

**Option C — APK ou lien de build Expo (distribution exigée par §6.3)** : nécessite un compte Expo
gratuit et `eas build -p android --profile preview` ; **non préparé** (décision et compte du responsable).

### Grille d'acceptation mobile (à remplir pendant la répétition)

| # | Critère | Résultat | Preuve (capture, vidéo) |
|---|---|---|---|
| M1 | L'application démarre sans erreur sur l'appareil ou l'émulateur (nommer lequel) | ☐ | |
| M2 | La liste des produits s'affiche depuis l'**API publique** (≥ 150 produits) | ☐ | |
| M3 | Le filtre par catégorie réduit la liste | ☐ | |
| M4 | Les produits sans image affichent la vignette de remplacement | ☐ | |
| M5 | API en veille : le premier chargement aboutit (délai 60 s, PR #51) ou le bouton « Réessayer » fonctionne | ☐ | |
| M6 | Mode avion : message d'erreur clair, pas de plantage | ☐ | |

Le client mobile du L1 affiche la **liste des produits** (exigence A.11) ; la recherche, la fiche et
les disponibilités sont démontrées sur le web et le bureau.

### Grille d'acceptation web et bureau

| # | Critère | Résultat | Preuve |
|---|---|---|---|
| W1 | Catalogue, tri, pagination | ☐ | |
| W2 | Recherche « drill » et « equerre » | ☐ | |
| W3 | Fiche `PERC-18V` : prix, caractéristiques, disponibilité par magasin, aucune quantité | ☐ | |
| W4 | Image de remplacement visible | ☐ | |
| W5 | Bascule FR/EN | ☐ | |
| W6 | Connexion, compte, déconnexion (comptes de démonstration créés) | ☐ | |
| W7 | Personnel sans MFA → `/compte/mfa` → code → session ouverte (#55) | ☐ | |
| W8 | `/admin` : modification d'un prix visible sur le site (#55) | ☐ | |
| W9 | `/confidentialite` accessible depuis l'inscription, marquée « à valider » (#55) | ☐ | |
| B1 | Bureau : l'exécutable du paquet `desktop-release` démarre sans installation de .NET | ☐ | |
| B2 | Bureau : la liste des produits vient de l'API publique (≥ 150 produits) | ☐ | |
| B3 | Bureau : la recherche filtre la liste | ☐ | |
| B4 | Bureau : API en veille → premier chargement abouti (délai 60 s) ou message clair et « Réessayer » | ☐ | |

## 4. Questions probables

| Question | Réponse et preuve |
|---|---|
| Comment évitez-vous la survente ? | Contraintes `0 ≤ reserved ≤ on_hand`, grand livre en ajout seulement, verrou `FOR UPDATE` (ADR-001, ADR-005) ; test de charge prévu au L2. |
| Le stock est-il public ? | Non : seul un statut est renvoyé ; un test vérifie l'absence de quantités. |
| Pourquoi la recherche trouve « équerre » avec « equerre » ? | `fr_unaccent`/`en_unaccent`, `search_vector` généré, index GIN (ADR-006). |
| Qui peut modifier le catalogue ? | L'administrateur ayant complété la MFA ; matrice des rôles testée sur toutes les routes. |
| Comment un fichier malveillant est-il bloqué ? | Type déduit des octets, taille et dimensions bornées, nom généré par le serveur, SVG refusé (ADR-009, #49). |
| Où sont les secrets ? | Tableaux de bord de Render et Vercel ; Gitleaks et secret scanning ; aucun dans Git. |
| Pourquoi l'API est-elle lente au premier appel ? | Mise en veille de l'offre gratuite de Render ; délai des clients porté à 60 s. |
| Qu'est-ce qui n'est pas fait ? | Voir les limitations des notes de version. |

## 5. Plan de repli

Si l'hébergement est indisponible : démonstration locale (base PostgreSQL 16 + amorçage, `uvicorn`,
`npm run dev`, `npx expo start`, `dotnet run`). **Le dire explicitement** : l'artéfact 6 exige un
déploiement en ligne, que la démonstration locale ne remplace pas.
