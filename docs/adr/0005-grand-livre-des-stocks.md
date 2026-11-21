# ADR-005 — Mouvements de stock signés dans un grand livre en ajout seulement

- **Statut :** Accepté par le responsable (orientations D3 et O6, 21 novembre 2026) — implémenté dans la PR #29, non fusionné.
- **Exigences :** A-INV-01 (« chaque changement est enregistré »), A-INV-02, A-CAT-02, ADR-001.

## Contexte

Le stock courant (`inventory.on_hand`) doit pouvoir être justifié par l'historique des mouvements, et
cet historique ne doit pas être altérable. Les stocks d'amorçage du L1 doivent déjà respecter ce
principe pour ne pas être repris au L2.

## Décision

- `stock_movements.quantity` est **signée** (positive = entrée, négative = sortie) ; une contrainte
  CHECK impose le signe selon le type (`receipt`, `return`, `transfer_in`, `reservation` > 0 ; `sale`,
  `transfer_out`, `release` < 0 ; `adjustment` ≠ 0 avec motif obligatoire).
- Le grand livre est **en ajout seulement** : un déclencheur PostgreSQL refuse UPDATE et DELETE.
  TRUNCATE (opération d'administration) n'est pas bloqué.
- Clé étrangère composée `(product_id, store_id)` vers `inventory` ; `order_id` référence `orders`.
- Toute variation de `on_hand` passe par le service (`record_movement`, verrou `SELECT … FOR UPDATE`),
  dans la même transaction que le mouvement. L'amorçage crée chaque ligne de stock avec son mouvement
  `receipt`.
- Invariant vérifié par les tests : `on_hand` = somme des mouvements physiques.

## Conséquences

- La sémantique de `reservation` et `release` (colonne `reserved`) sera fixée au L2 avec les
  commandes ; le service les refuse d'ici là.
- Une erreur se corrige par un nouveau mouvement `adjustment`, jamais par une modification.
