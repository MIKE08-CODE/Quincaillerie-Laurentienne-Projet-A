# Recette finale et livraison — L1 v0.1.0

Guide unique des dernières étapes. Ordre recommandé : de haut en bas. Chaque étape dit **qui** agit,
ce qui est **attendu**, et où consigner la **preuve** (identifiants P1 à P11 du
[registre des preuves](registre-preuves-l1.md)). Aucune étape n'est réputée faite sans vérification réelle.

Adresses :

- Site : https://quincaillerie-laurentienne-seven.vercel.app
- API : https://quincaillerie-laurentienne-api.onrender.com (documentation : `/docs`)
- Tableau : https://github.com/users/MIKE08-CODE/projects/1

## 0. Préparation de chaque séance (5 minutes)

1. Ouvrir `https://quincaillerie-laurentienne-api.onrender.com/health`. Attendu : `{"status":"ok"}`.
   Le premier appel peut prendre jusqu'à une minute (mise en veille de l'offre gratuite).
2. Ouvrir le site. Attendu : la page d'accueil et le catalogue (157 produits).

## 1. Démonstration web W1 à W9 (responsable, navigateur)

| # | Action exacte | Attendu |
|---|---|---|
| W1 | Catalogue → choisir une catégorie → trier par prix → page suivante | Liste paginée (24 par page), tri appliqué |
| W2 | Rechercher `drill`, puis `equerre` | Perceuses trouvées ; « Équerre … » trouvées sans accent |
| W3 | Ouvrir la fiche `PERC-18V` | Prix, caractéristiques, disponibilité par magasin (« En stock », « Stock faible », « Rupture »), **aucune quantité** |
| W4 | Fiche d'un produit sans image téléversée | Vignette « sans image » ; sur ADHE-COLB, l'image Cloudinary |
| W5 | Bouton « English » | Interface en anglais, retour en français |
| W6 | `/connexion` avec `demo-client@example.com` → « Mon compte » → déconnexion | Rôle « Client » ; mauvais mot de passe → message neutre |
| W7 | Connexion `demo-commis@example.com` (MFA pas encore configurée) | Redirection vers `/compte/mfa`, clé affichée, code accepté, session ouverte |
| W8 | Administrateur (code MFA) → `/admin` → modifier le prix d'un produit → fiche publique | Nouveau prix visible ; remettre le prix d'origine ensuite |
| W9 | `/inscription` → lien « politique de confidentialité » | `/confidentialite` affichée, mention « ÉBAUCHE À VALIDER » tant que la section 6 n'est pas faite |

Preuves : captures W1 à W9 (P2, P11). Masquer toute adresse réelle.

## 2. Démonstration mobile M1 à M6 (responsable, téléphone Android ou émulateur)

1. Installer **Expo Go** (Google Play, gratuit). Vérifier dans l'application qu'elle prend en charge le
   **SDK 58** ; sinon, utiliser un émulateur Android Studio (gratuit).
2. Dans Git Bash, à la racine du dépôt (le fichier est ignoré par Git) :
   ```bash
   cd mobile && npm ci
   printf 'EXPO_PUBLIC_API_BASE_URL=https://quincaillerie-laurentienne-api.onrender.com/api/v1\n' > .env.production
   npx expo start --tunnel
   ```
3. Scanner le code QR avec Expo Go (ou touche `a` pour l'émulateur).

| # | Critère | Attendu |
|---|---|---|
| M1 | L'application démarre | Aucune erreur ; noter l'appareil ou l'émulateur |
| M2 | Liste des produits | Produits de l'API publique (157 au total) |
| M3 | Filtre par catégorie | La liste se réduit à la catégorie choisie |
| M4 | Produit sans image | Vignette de remplacement |
| M5 | API en veille | Premier chargement abouti (délai 60 s) ou « Réessayer » fonctionnel |
| M6 | Mode avion | Message d'erreur clair, pas de plantage |

Preuves : captures ou courte vidéo (P4).

## 3. Démonstration bureau B1 à B4 (responsable, Windows)

1. Obtenir le paquet. Avant l'étiquette, le workflow `desktop-release` vérifie le paquet mais **ne le
   publie pas** ; on le construit donc sur le poste, depuis `main` (PowerShell, racine d'un dossier de
   travail propre) :
   `./desktop/scripts/package.ps1 -ApiUrl https://quincaillerie-laurentienne-api.onrender.com/api/v1 -Version v0.1.0-recette`.
   Après l'étiquette `v0.1.0`, le paquet officiel est joint à la version GitHub (section 10).
2. Vérifier l'empreinte, dans PowerShell, dans le dossier du ZIP :
   `Get-FileHash .\<fichier>.zip -Algorithm SHA256`. Comparer avec le fichier `.sha256` du paquet.
3. Extraire, puis lancer `QuincaillerieLaurentienne.Desktop.exe`. Aucun runtime .NET n'est à installer ;
   `appsettings.json` pointe déjà vers l'API publique. Si Windows bloque un exécutable non signé
   (SmartScreen ou contrôle intelligent des applications), le noter dans la grille : c'est une limite de
   distribution connue (signature de code non exigée au L1).

| # | Critère | Attendu |
|---|---|---|
| B1 | L'exécutable démarre | Fenêtre ouverte, sans installation de .NET |
| B2 | Liste des produits | Produits de l'API publique (≥ 150) |
| B3 | Recherche | La liste est filtrée |
| B4 | API en veille | Premier chargement abouti (délai 60 s) ou message clair et « Réessayer » |

SmartScreen : « Informations complémentaires » → « Exécuter quand même ». Preuves : captures (P5).

## 4. Clôture de l'issue #7 (A-CAT-01)

Critères de l'issue : listes paginées (50 au maximum par page) ; navigation par catégorie sur le web
**et** le mobile.

| Critère | État |
|---|---|
| Pagination bornée | Technique : `size=100` refusé (422) en production ; `size=50` accepté |
| Catégorie sur le web | Technique (tests du web) ; à montrer en W1 |
| Catégorie sur le mobile | **À démontrer (M3)** |

Après la réussite de M3, l'issue est fermée avec la capture en preuve (par l'outillage sur
confirmation du responsable, ou par `gh issue close 7`).

## 5. Données réelles de gestion de projet (équipe)

Remplir [`donnees-equipe-a-completer.md`](donnees-equipe-a-completer.md) : membres et rôles, dates et
objectifs des sprints 1 à 3, rétrospectives, responsable de chaque élément, feuilles de temps, réunions
réellement tenues. **Aucune valeur estimée après coup sans le signaler.** Ensuite, l'outillage recopie
ces valeurs dans le tableau (champs Sprint, Responsable, Heures), les rapports de sprint et
`docs/meetings/`, par une PR.

## 6. Validation des ADR (responsable)

| ADR | Sujet | Statut actuel |
|---|---|---|
| 001 à 003 | Verrouillage du stock, stockage des jetons, cadre mobile (dans `docs/architecture/architecture_Quincaillerie_Laurentienne.md`) | Proposé |
| 004 | Marques : entité dédiée | Accepté |
| 005 | Grand livre des stocks | Accepté |
| 006 | Recherche plein texte | Accepté |
| 007 | React 19 sur le mobile (Expo SDK 58) | Proposé |
| 008 | Format uniforme des erreurs | Accepté dans son principe |
| 009 | Stockage des images (Cloudinary) | Proposé ; implémenté et testé en production |

Pour chaque ADR « Proposé », répondre « Accepté » ou « À revoir (motif) ». L'outillage passe ensuite
le statut à « Accepté (date, responsable) » par une PR, et la décision est consignée au procès-verbal.

## 7. Validation de la politique de confidentialité (responsable)

Champs à fournir pour `/confidentialite` (français et anglais) :

1. Responsable de la protection des renseignements personnels : nom et coordonnées.
2. Adresse de contact.
3. Région de l'API Render : Render → service → **Settings** → **Region**.
4. Durée de conservation des comptes, des consentements et des journaux.
5. Procédure et délai de réponse pour l'accès, la rectification, le retrait du consentement et la suppression.

Ensuite, l'outillage complète la page, retire la mention « ÉBAUCHE À VALIDER » par une PR, et la
validation est consignée au procès-verbal. Sans ces données, la politique reste une ébauche, ce qui
est déclaré comme limitation dans les notes de version.

## 8. Recette finale (responsable)

- [ ] W1 à W9, M1 à M6, B1 à B4 réussis et capturés.
- [ ] A-AUTH-01 testé en réel (inscription → courriel de vérification → « adresse vérifiée »), preuve P6.
- [ ] Captures C2 à C8 archivées (P10).
- [ ] Issue #7 fermée.
- [ ] Données de l'équipe fournies et recopiées (P8).
- [ ] ADR et politique de confidentialité tranchées.
- [ ] Écart §6.1 tranché : coéquipier ajouté et 1 approbation exigée, ou écart accepté au procès-verbal.
- [ ] Alerte Dependabot n° 2 : exception conservée ou fermée avec motif.
- [ ] Procès-verbal signé (P9).

## 9. Distribution des applications

| Application | Distribution L1 | Remarque |
|---|---|---|
| Web | URL du site (ci-dessus) | Déployé automatiquement à chaque fusion sur `main` |
| API | URL de l'API, `/docs` | Idem |
| Bureau | ZIP autonome et empreinte SHA-256, joints automatiquement à la version GitHub en brouillon lors de la poussée de l'étiquette | Avant l'étiquette : paquet construit sur le poste (section 3) |
| Mobile | Expo Go (section 2) | APK ou lien Expo exigés au **L3** (§9.3) : compte Expo gratuit et `eas build`, non préparé |

## 10. Publication de v0.1.0 (après autorisation écrite du responsable seulement)

```bash
git switch main && git pull --ff-only
git tag -a v0.1.0 -m "L1 — Fondations"
git push origin v0.1.0
```

La poussée de l'étiquette lance `desktop-release`, qui crée la version GitHub **en brouillon** avec le
paquet Windows ; y coller les notes de [`notes-de-version-v0.1.0.md`](notes-de-version-v0.1.0.md) et
l'URL du site, relire, puis publier (`gh release edit v0.1.0 --draft=false`).
