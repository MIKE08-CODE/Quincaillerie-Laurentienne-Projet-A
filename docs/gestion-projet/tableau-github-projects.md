# Tableau GitHub Projects — L1

**Tableau :** <https://github.com/users/MIKE08-CODE/projects/1> (« @MIKE08-CODE's Quincaillerie Laurentienne –
Projet A »), créé par le responsable et **complété le 22 novembre 2026** à partir de données vérifiables
seulement (aucun élément ni statut existant retiré ou modifié par l'outillage).

## Contenu vérifié (60 éléments, aucun doublon)

| Type | Nombre | Détail |
|---|---|---|
| Issues | 23 | #1 à #27 (dont les exigences L1 #1 à #10) |
| PR | 29 | Les 20 PR fusionnées de la L1 (#21 à #52) et 9 PR Dependabot |
| Éléments L1 sans issue | 8 | Amorçage, déploiement, clients connectés, courriels, comptes de démonstration, gestion de projet, démonstration de 20 min, version v0.1.0 |

## Champs

| Champ | Type | Valeurs | Source |
|---|---|---|---|
| Status (existant) | Sélection | Backlogs, Todo, In Progress, In Reviews, Done | Responsable (non modifié) |
| Sprint | Sélection | Sprint 1, 2, 3 (« dates à compléter »), À compléter | **« À compléter » partout** : la répartition par sprint n'est documentée nulle part |
| Priorité | Sélection | Must, Should, Could, À compléter | Étiquette `must` des issues #1 à #10 ; « À compléter » sinon |
| Jalon | Sélection | L1, L2, L3, À compléter | Cahier A.11 et contenu des PR |
| Application | Sélection | API, Web, Mobile, Bureau, Clients, DevOps, Documentation, Gestion de projet | Fichiers modifiés par les PR |
| Exigence | Texte | A-AUTH-01, A-CAT-02, §6.3, artéfact 8… | Titres des issues, matrice de traçabilité |
| PR fusionnées | Texte | Numéros des PR liées | Historique GitHub |
| Responsable | Texte | **À compléter** (aucune issue n'a d'assigné) ; pour les PR : auteur MIKE08-CODE | GitHub |
| Heures | Texte | **À compléter** | Aucune donnée d'heures dans le dépôt |
| Preuve / remarque | Texte | État vérifié et preuve (tests, vérification en production) | Matrice de traçabilité |

## À faire par l'équipe

1. Pour chaque élément : choisir le **Sprint** réel et le **Responsable** réel ; saisir les **Heures** ou
   renvoyer aux feuilles de temps.
2. Ajouter une **vue en colonnes** (Board) groupée par `Status`, et une vue groupée par `Sprint` (les vues
   ne peuvent pas être créées en ligne de commande).
3. Aligner `Status` sur l'état vérifié si souhaité : #6 à #9 sont fusionnés et vérifiés en production
   (actuellement « Backlogs ») ; #10 est en cours (stockage des images à activer).
4. Faire une capture du tableau rempli (preuve P7 de la matrice).

> Remarque de traçabilité : certaines PR citent une issue de façon approximative (p. ex. #38, comptes de
> démonstration, indique « Refs #6 » alors qu'elle relève de §6.3). Le champ « PR fusionnées » du tableau et
> la [matrice](matrice-tracabilite-l1.md) donnent le rattachement exact.
