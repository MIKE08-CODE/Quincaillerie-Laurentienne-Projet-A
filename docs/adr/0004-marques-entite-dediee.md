# ADR-004 — Les marques sont une entité dédiée (`brands`)

- **Statut :** Accepté par le responsable (orientation D2, 21 novembre 2026) — implémenté dans la PR #29, non fusionné.
- **Exigences :** A-ADM-01 (« CRUD … des catégories et des marques »), A-CAT-04 (filtre par marque, Should).

## Contexte

A.6 décrit `brand` comme un simple attribut texte de `products`, mais A-ADM-01 exige un CRUD des
marques. Une marque doit donc pouvoir exister, être renommée ou désactivée indépendamment des
produits. A.6 précise que « d'autres entités peuvent être ajoutées ».

## Options

1. Table `brands` et clé étrangère `products.brand_id`.
2. Champ texte `products.brand` et « gestion » dérivée (renommer = modifier tous les produits).
3. Table `brands` et nom recopié dans `products.brand`.

## Décision

Option 1, **sans duplication du nom** : `brands(id, name, slug, is_active, created_at, updated_at)`,
nom unique sans tenir compte de la casse par un index unique sur `lower(name)` (même mécanisme que
`users.email`, sans extension `citext`), suppression = désactivation logique. Les réponses publiques
exposent toujours `brand` (le nom, par jointure) pour rester compatibles avec le contrat.

## Conséquences

- Écart documenté avec l'attribut `brand` de A.6.
- Une marque désactivée ne peut plus être attribuée (422 `brand_inactive`), mais reste affichée sur
  les produits existants.
- Le nom de la marque n'entre pas dans la recherche plein texte (voir ADR-006).
