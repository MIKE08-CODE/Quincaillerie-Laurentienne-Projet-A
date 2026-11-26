# Registre des risques — L1

Mis à jour le **22 novembre 2026**. Échelle : probabilité et impact de 1 (faible) à 3 (élevé) ; criticité =
probabilité × impact. **Responsables : à confirmer par l'équipe** (MIKE08-CODE indiqué quand il est le seul
à pouvoir agir).

## Risques ouverts

| ID | Risque | P | I | C | Mesure | État | Responsable |
|---|---|---|---|---|---|---|---|
| R2 | **Courriels non envoyés en production** : inscription et réinitialisation impossibles en ligne | 3 | 3 | 9 | Code prêt (Brevo, PR #35) ; pages web (PR #50) ; procédure de configuration (guide de déploiement, D1) | Ouvert — **action du responsable** | MIKE08-CODE |
| R8b | **Gestion de projet sans données réelles** (tableau, sprints, heures, comptes rendus) | 3 | 3 | 9 | Gabarits prêts ; aucune donnée inventée | Ouvert — **action de l'équipe** | Équipe |
| R10 | Client mobile jamais exécuté sur un appareil ou un émulateur | 2 | 3 | 6 | Procédure et grille d'acceptation (`plan-demonstration-l1.md` §3) ; délai de 60 s (PR #51) | Ouvert | À confirmer |
| R12 | Contradiction d'échéancier du cahier (L1 en semaine 2 ou 3) | 2 | 3 | 6 | À arbitrer par le responsable (point ouvert O16) | Ouvert | Responsable du projet |
| R4 | Un seul développeur fusionne, sans relecture (0 approbation, §6.1 en exige 1) | 2 | 3 | 6 | CI obligatoire, fils résolus ; écart consigné | Accepté (décision du responsable) | MIKE08-CODE |
| R15 | **Images** : stockage persistant non activé (503 en production) | 2 | 2 | 4 | Validation (#49), adaptateur Cloudinary testé sans réseau (#54), interface `/admin` (#55) ; activation : décision 4 de `decisions-et-validations-l1.md` | Ouvert — décision requise | MIKE08-CODE |
| R16 | PR Dependabot de versions **majeures** | 1 | 1 | 1 | Traitées le 26 novembre 2026 : #44, #45, #47 fusionnées ; #43 et #48 remplacées par #60 et #61 ; #46 remplacée par #57 ; #42 (React 19.3.1 mobile) non fusionnée, incompatible avec Expo SDK 58 | Fermé | MIKE08-CODE |
| R14 | **Alerte Dependabot n° 2** — `minimatch` GHSA-g3hv-75wg-m249 (déni de service par motifs glob, modérée), voir détail ci-dessous | 1 | 1 | 1 | Exception documentée dans `mobile/scripts/audit-check.mjs` ; **réévaluation au plus tard le 2026-12-21** | Toléré (fermeture de l'alerte : décision du responsable) | MIKE08-CODE |
| R6 | PR Dependabot #24 bloquée (Ruff UP042, issue #26) ; #25 (`argon2-cffi` 25) en attente | 1 | 1 | 1 | #58 (`StrEnum`) puis #24 et #25 fusionnées le 26 novembre 2026 ; 426 tests verts ; dépréciations retirées (#59) | Fermé | MIKE08-CODE |
| R5 | Écart entre le contrat d'API et le code (format d'erreur) | 2 | 2 | 4 | ADR-008 ; écart consigné au §18 du contrat | Ouvert | À confirmer |
| R9 | Mise en veille de l'API gratuite pendant la démonstration | 2 | 2 | 4 | Réveil 15 min avant ; clients à 60 s (PR #51) ; plan de repli local | Atténué | Présentateur |
| R13 | Charge de travail : trois clients, l'API et le déploiement | 3 | 2 | 6 | Périmètre minimal L1 pour le mobile et le bureau ; priorisation par issues | Ouvert | À confirmer |
| R17 | Politique de confidentialité en ébauche non validée (Loi 25) | 2 | 2 | 4 | Ébauche fidèle aux traitements réels, liée à l'inscription (#55) ; champs « À compléter » | Ouvert — validation requise | Responsable du projet |
| R18 | Distribution exigée par §6.3 absente (bureau sur GitHub Releases, APK ou lien Expo) | 2 | 2 | 4 | À produire avec la version `v0.1.0` (autorisation requise) | Ouvert | MIKE08-CODE |
| R11 | Deux versions majeures de React (web 18, mobile 19) | 1 | 1 | 1 | ADR-007 ; aucun code partagé | Accepté sous réserve d'approbation | À confirmer |

### Détail de R14 (alerte Dependabot n° 2)

| Élément | Constat (22 novembre 2026) |
|---|---|
| Avis | GHSA-g3hv-75wg-m249 : `minimatch` `>= 7.0.0, < 11.0.1`, correctif 11.0.1 (version **majeure**) |
| Copies concernées | `10.2.6` via `@expo/fingerprint` (outil de build d'Expo) ; `9.0.9` et `10.2.6` via Jest (tests) ; `3.1.5` non concernée |
| Exposition réelle | Aucune dans l'application livrée : ces paquets ne sont **pas embarqués** dans le bundle mobile et ne tournent ni sur le serveur ni sur le téléphone. Les motifs glob viennent de la configuration du projet, **jamais d'une saisie d'utilisateur**. |
| Correctif amont | Aucun : la dernière version (et les versions canary) de `@expo/fingerprint` exigent `minimatch ^10.2.2` |
| Mesure tentée | Surcharge npm limitée aux versions 7 à 11.0.1 : **abandonnée** (lockfile incohérent, `npm ls` signale des dépendances `invalid`) ; aucune mise à jour forcée |
| Atténuation | Exception ciblée et datée dans `mobile/scripts/audit-check.mjs` (l'audit échoue pour toute autre vulnérabilité) ; Dependabot npm actif sur `/mobile` |
| Réévaluation | Au plus tard le **2026-12-21**, ou dès qu'Expo publie une version compatible avec `minimatch` ≥ 11.0.1 |

## Risques fermés ou maîtrisés depuis le 21 novembre

| ID | Risque | Résolution | Preuve |
|---|---|---|---|
| R1 | L1 non déployée | API et web en ligne | `docs/deploiement/deploiement-l1.md` §7 |
| R3 | Accumulation de PR non fusionnées | #28 à #41 fusionnées par squash, contrôles vérifiés | Historique de `main` |
| R7 | `unaccent` indisponible sur Neon | Migrations appliquées ; recherche sans accents vérifiée en production | HTTP : `equerre` = `équerre` = 5 |
| R8 | IP du client falsifiable derrière les relais | `CLIENT_IP_HEADER=cf-connecting-ip` ; falsification sans effet, `CF-Connecting-IP` inventé rejeté par Cloudflare | PR #35 ; vérification du 2026-11-21 |
