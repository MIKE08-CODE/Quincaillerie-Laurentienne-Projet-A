# Décisions et validations humaines — L1 v0.1.0

**Aucune de ces décisions n'est acquise.** Chacune exige une action explicite du responsable du projet ;
la procédure est donnée pour qu'elle soit courte et vérifiable. Ordre recommandé : de haut en bas.

## 1. Fusionner les PR prêtes — **fait**

#54, #55 et #56 fusionnées le 23 novembre 2026. Le 26 novembre 2026, sur autorisation globale : PR
Dependabot #57, #44, #24, #47, #45, #25 et PR correctives #58 à #61 fusionnées (détail en section 10).

## 2. Fermer les issues dont les critères sont satisfaits (#6, #8, #9)

L'outillage a vérifié les critères, mais la fermeture lui a été refusée par les permissions de la
session : elle revient au responsable. Commandes prêtes (texte de preuve inclus) :

```bash
gh issue close 6 --comment "Critère satisfait (script de test) : test_lockout.py, test_client_ip.py ; production 2026-11-21 : 120 × 200 et 20 × 429 sur 140 requêtes, IP falsifiée sans effet. PR #21, #35."
gh issue close 8 --comment "Critère satisfait : statut calculé par inventory_service.availability_status à partir des stocks ; test_availability_is_computed_from_real_stock ; production : statut par magasin, aucune quantité exposée."
gh issue close 9 --comment "Critères satisfaits : perceuse 13 et drill 14 résultats ; equerre = équerre = 5 ; test_search_finds_drills_in_french_and_english, test_search_is_accent_insensitive ; ADR-006."
```

**#7 reste ouverte** jusqu'à la démonstration mobile de la navigation par catégorie (grille M3).
**#10 reste ouverte** jusqu'au test réel du téléversement (décision 4).

## 3. Courriels Brevo (A-AUTH-01, A-AUTH-04)

1. Créer un compte gratuit sur brevo.com (sans carte), confirmer une adresse d'expédition, créer une clé d'API.
2. Render → service de l'API → *Environment* : `EMAIL_BACKEND=brevo`, `EMAIL_FROM_ADDRESS=<adresse confirmée>`,
   `BREVO_API_KEY=<clé>` (secret), `WEB_BASE_URL=https://quincaillerie-laurentienne-seven.vercel.app`.
3. **Me prévenir** : je vérifie le redémarrage (`/health`), puis vous faites le test réel — inscription sur
   `/inscription` avec **votre** adresse, lien reçu → « adresse vérifiée » ; `/mot-de-passe-oublie` → lien →
   nouveau mot de passe → connexion. Captures = preuve P6. Les courriels ne sont déclarés fonctionnels
   qu'après ce test.

## 4. Stockage des images — Cloudinary (ADR-009)

Décider : **activer Cloudinary** (recommandé, offre gratuite sans carte) **ou** accepter pour la L1 la limitation
« images par URL https seulement, téléversement 503 ».

Si activation (après fusion de #54) : compte gratuit sur cloudinary.com, puis Render → *Environment* :
`IMAGE_STORAGE_BACKEND=cloudinary`, `CLOUDINARY_CLOUD_NAME=<nom du compte>`, `CLOUDINARY_API_KEY=<clé>`,
`CLOUDINARY_API_SECRET=<secret>` (secret). Test réel : `/admin` (après #55) → téléverser un JPEG → l'image
s'affiche sur la fiche ; retirer l'image → elle disparaît du tableau de bord Cloudinary.

## 5. Comptes de démonstration

Autoriser explicitement leur création en production, puis suivre `procedure-comptes-demo.md` (mots de
passe saisis par vous dans un terminal, jamais écrits). Configurer ensuite la MFA du commis, du gérant et
de l'administrateur depuis `/compte/mfa` (PR #55).

## 6. Politique de confidentialité

Relire `/confidentialite` (PR #55) : compléter responsable, contact, durée de conservation, région Render
et évaluation des facteurs relatifs à la vie privée ; puis retirer la mention « ÉBAUCHE À VALIDER » par
une PR. Tant que ce n'est pas fait, le texte reste une ébauche.

## 7. Interface d'administration

Décider si l'interface minimale de #55 (`/admin` : liste, nom, prix, visibilité, images) suffit pour la L1.
Les catégories et les marques restent gérées par l'API (`/docs`, routes `/api/v1/admin/categories` et
`/brands`, testées) ; leur interface web relève de l'issue #17.

## 8. Écart §6.1 — approbation obligatoire des PR

Constat : ruleset `protect-main` (id `27773677`) : `required_approving_review_count = 0`, un seul
collaborateur (MIKE08-CODE). **Exiger 1 approbation aujourd'hui bloquerait toute fusion** (GitHub interdit
d'approuver sa propre PR). Correction exacte, sans affaiblir l'existant :

1. Ajouter au moins un coéquipier avec le droit d'écriture (Paramètres → Collaborators).
2. Puis, dans le ruleset (Paramètres → Rules → `protect-main`) : `Required approvals` = **1**,
   `Dismiss stale pull request approvals when new commits are pushed` = **oui**,
   `Require approval of the most recent reviewable push` = **oui** ; ne pas ajouter de contournement.
3. Indépendamment (sans risque de blocage, recommandé dès maintenant) : ajouter `web-ci`, `mobile-ci` et
   `desktop-ci` aux contrôles obligatoires ; ces workflows publient un résultat sur **toutes** les PR
   (vérifié sur les PR documentaires #52 et #53).

Si aucun coéquipier n'existe : consigner l'écart comme accepté (procès-verbal, risque R4).

## 9. Alerte Dependabot n° 2 (`minimatch`)

Revérifié le 23 novembre 2026 : `@expo/fingerprint` 0.21.10 (dernière) exige toujours `minimatch ^10.2.6`
(vulnérable jusqu'à 11.0.1) ; Expo 58.0.26 est la dernière version. **Aucun correctif compatible.**
Décider : conserver l'alerte ouverte avec l'exception documentée (risque R14, réévaluation au plus tard le
2026-12-21), ou la fermer dans GitHub avec la raison « risque toléré » (action du responsable).

## 10. PR Dependabot — **traitées le 26 novembre 2026**

| PR | Mise à jour | Résultat |
|---|---|---|
| #57 | `i18next` 27.2.7 (web) | Fusionnée ; corrige les alertes Dependabot n° 3 et 4 (GHSA-6jcc-5g8w-32mx) |
| #46 | `i18next` 27.2.1 | Fermée par Dependabot (remplacée par #57) |
| #47 | `react-i18next` 18 | Fusionnée (React 18 pris en charge ; l'application n'utilise que `useTranslation`) |
| #45 | `@testing-library/jest-dom` 8 | Fusionnée |
| #44 | TypeScript 7 (mobile) | Fusionnée (types, tests et bundle Android verts) |
| #24 | 9 paquets Python (SQLAlchemy 2.1, Alembic 1.20, Uvicorn 0.54, Ruff 0.17…) | Fusionnée après #58 (`StrEnum`, règle UP042) ; dépréciations retirées par #59 |
| #25 | `argon2-cffi` 25.1.0 | Fusionnée (hachages existants vérifiables, mêmes paramètres) |
| #43 | `@eslint/js` 10 | Remplacée par #60 (ESLint 10 et `eslint-plugin-react-hooks` 7, `useApi` revu) ; fermée par Dependabot |
| #48 | Vite 8 | Remplacée par #61 (Vite 8 et `@vitejs/plugin-react` 6) ; fermée par Dependabot |
| #42 | React 19.3.1 (mobile) | **Non fusionnée** : Expo SDK 58 et React Native 0.88.1 imposent React 19.3.0 ; laissée à Dependabot |

Chaque fusion : branche à jour avec `main`, tous les contrôles verts, liste exacte des fichiers vérifiée, squash.
Après #24 : déploiement Render réussi et recherche de production inchangée (perceuse 13, drill 14, équerre 5) ;
après #61 : le site de production sert le bundle construit localement avec Vite 8.

## 11. Validations documentaires

Lire puis approuver (ou demander des corrections) : vision et exigences ; ADR 001 à 009 (statut
« Proposé ») ; modèle de menaces STRIDE ; documentation finale. Une approbation se consigne dans le
procès-verbal (`proces-verbal-approbation-l1.md`) et, pour les ADR, par une PR qui passe le statut à « Accepté ».

## 12. Remise

Répéter la démonstration (`plan-demonstration-l1.md`), remplir `donnees-equipe-a-completer.md`, faire
signer le procès-verbal, puis autoriser la version :

```bash
git switch main && git pull --ff-only
git tag -a v0.1.0 -m "L1 — Fondations"      # après autorisation seulement
git push origin v0.1.0
```

La poussée de l'étiquette lance `desktop-release`, qui crée la version GitHub **en brouillon** avec le
paquet Windows et les notes ; la relire puis la publier (`gh release edit v0.1.0 --draft=false`).
