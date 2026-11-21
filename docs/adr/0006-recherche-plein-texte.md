# ADR-006 — Recherche plein texte FR/EN par colonne générée et configurations `*_unaccent`

- **Statut :** Accepté par le responsable (orientation O9, « A′ », 21 novembre 2026), validé par un essai isolé — implémenté dans la PR #29, non fusionné.
- **Exigence :** A-CAT-03 (« perceuse » et « drill » trouvent les perceuses ; « equerre » trouve « équerre »).

## Contexte

`unaccent()` est `STABLE`, donc refusée dans une colonne générée ou une expression d'index. Trois
options ont été comparées : fonction enveloppe déclarée `IMMUTABLE` (A), configurations de recherche
avec filtre `unaccent` (A′), déclencheur (B).

## Décision

Option A′ : configurations `public.fr_unaccent` et `public.en_unaccent` (copies de `french` et
`english`, `unaccent` appliqué avant la racinisation) ; `products.search_vector` est une colonne
`GENERATED ALWAYS AS … STORED` (noms FR/EN poids A, descriptions FR/EN poids C), indexée en GIN. La
requête combine `websearch_to_tsquery('fr_unaccent', q) || websearch_to_tsquery('en_unaccent', q)`,
triée par `ts_rank_cd`.

## Conséquences

- Aucune fonction « faussement immuable » écrite par l'équipe ; l'immuabilité repose sur celle de
  `to_tsvector(regconfig, text)`.
- Une colonne générée ne lit pas d'autre table : la marque n'est pas cherchable par texte.
- PostgreSQL 16 ne modifie pas l'expression d'une colonne générée : changer la formule impose de
  supprimer et recréer la colonne. Alembic ne compare pas l'expression : un test le fait.
- Comportements observés et documentés : la racinisation élargit (« drill » trouve « self-drilling ») ;
  la configuration `french` ne traite pas « les » comme un mot vide.
