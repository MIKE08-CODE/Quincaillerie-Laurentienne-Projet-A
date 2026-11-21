# Tableau GitHub Projects — proposition

**État : non créé.** Le jeton GitHub utilisé n'a pas le droit `project` (`gh project list` refuse :
« missing required scopes [read:project] »). Pour le créer :

```bash
gh auth refresh -s project      # à lancer par le propriétaire du dépôt
gh project create --owner MIKE08-CODE --title "Quincaillerie Laurentienne — Projet A"
```

## Colonnes proposées

| Colonne | Règle |
|---|---|
| À faire | Issue prête (critères d'acceptation, jalon) |
| En cours | Branche ou PR ouverte |
| En revue | PR ouverte, CI verte |
| Terminé | PR fusionnée et issue fermée |

Champs : `Jalon` (L1, L2, L3), `Priorité` (Must, Should, Could), `Application` (API, web, mobile,
bureau, DevOps, documentation), `Estimation`.

## Rattachement initial (état réel au 2026-11-21)

| Élément | Colonne |
|---|---|
| #1 à #5 (A-AUTH-01 à 05), #11, #22 | Terminé |
| #6 A-AUTH-07 (code fusionné, issue encore ouverte) | En revue (vérifier puis fermer) |
| #7 à #10 (A-CAT-01 à 03, A-ADM-01) ← PR #29, #30 | En revue |
| #27 documents ← PR #28 | En revue |
| PR #31 mobile, #32 bureau, #33 DevOps | En revue |
| #12 architecture | En cours (PR #28 et PR de suivi) |
| #26 Ruff UP042 | À faire (en pause) |
| #13 à #20 (L2/L3) | À faire |
