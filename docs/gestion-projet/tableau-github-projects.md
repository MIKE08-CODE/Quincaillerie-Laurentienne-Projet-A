# Tableau GitHub Projects — L1

**État au 22 novembre 2026 : non créé.** Le jeton GitHub utilisé par l'outillage n'a que les droits
`repo`, `read:org` et `gist` ; `gh project list` refuse : « missing required scopes [read:project] ».

## Autorisation nécessaire (une seule commande, par le propriétaire du dépôt)

```bash
gh auth refresh -s project
```

Le navigateur demande de confirmer l'ajout du droit `project` (aucun mot de passe à transmettre). Le
tableau pourra ensuite être créé et rempli à partir des issues existantes, sans rien inventer.

## Structure proposée

| Colonne | Règle |
|---|---|
| À faire | Issue prête (critères d'acceptation, jalon) |
| En cours | Branche ou PR ouverte |
| En revue | PR ouverte, CI verte |
| Terminé | PR fusionnée et issue fermée |

Champs : `Jalon` (L1, L2, L3), `Priorité` (Must, Should, Could), `Application` (API, web, mobile,
bureau, DevOps, documentation), `Sprint` (S1 à S8), `Estimation`.

## Rattachement d'après l'état réel des issues et des PR

| Élément | Colonne | Remarque |
|---|---|---|
| #1 à #5 (A-AUTH-01 à 05), #11, #22, #27 | Terminé | Issues fermées |
| #6 A-AUTH-07 | En revue → Terminé | Code fusionné (#21, #35) et vérifié en production ; **fermeture : décision du responsable** |
| #7 A-CAT-01, #8 A-CAT-02, #9 A-CAT-03 | En revue → Terminé | Fusionnés (#29, #30, #39) et vérifiés en production ; **fermeture : décision du responsable** |
| #10 A-ADM-01 | En revue | Téléversement dans #49 ; stockage à activer (ADR-009) ; interface d'administration absente |
| #12 Document d'architecture | En revue | Contenu fusionné ; ADR « Proposé » à approuver |
| #17 Espace administrateur | À faire | Interface web d'administration |
| #26 Ruff UP042 | À faire | Débloque la PR Dependabot #24 |
| #13 à #16, #18 à #20 (L2/L3) | À faire | — |
| PR #49, #50, #51 | En revue | À fusionner sur autorisation |

> Remarque de traçabilité : certaines PR citent une issue de façon approximative (p. ex. #38, comptes de
> démonstration, indique « Refs #6 » alors qu'elle relève de §6.3). La matrice
> [`matrice-tracabilite-l1.md`](matrice-tracabilite-l1.md) donne le rattachement exact.
