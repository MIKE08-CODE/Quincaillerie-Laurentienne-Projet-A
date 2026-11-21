# Catalogue, stocks et entités Must — incrément L1

Exigences : A-CAT-01, A-CAT-02, A-CAT-03, A-ADM-01, A-INV-01 (grand livre), A.6 (modèle de données),
A.11 (migrations de toutes les entités Must, données d'amorçage).

Ce document décrit ce qui est **implémenté et testé** dans l'API. Les routes de panier, de commande et
de paiement ne font pas partie du L1 : seules leurs tables existent.

## 1. Migrations Alembic

| Révision | Parent | Contenu |
|---|---|---|
| `7217efbff6be` | — | Authentification (existant) |
| `aa6b82a168aa` | `7217efbff6be` | Sessions (existant) |
| `c4a1e7d2b9f0` | `aa6b82a168aa` | Extension `unaccent`, configurations `fr_unaccent` et `en_unaccent`, `categories` (+ déclencheur anti-cycle), `brands`, `products` (+ `search_vector` généré, index GIN), `product_images` |
| `d8b3f5a6c1e2` | `c4a1e7d2b9f0` | `inventory`, `stock_movements` (+ déclencheur « ajout seulement ») |
| `e2c9a4b7d3f1` | `d8b3f5a6c1e2` | `carts`, `cart_items`, `orders`, `order_items`, `order_status_history`, `payment_events`, clé étrangère `stock_movements.order_id` |

Chaque migration a un retour arrière exact, testé à chaque exécution de la suite (`downgrade base`
puis `upgrade head`, et un aller-retour ciblé dans `tests/test_catalog_schema.py`). L'absence de dérive
entre modèles et migrations est vérifiée par `alembic check` (test automatique).

## 2. Modèle

| Table | Points clés |
|---|---|
| `categories` | Arborescence auto-référencée (`parent_id`, RESTRICT), `slug` unique au format `a-z0-9-`, CHECK « pas son propre parent », déclencheur `categories_prevent_cycle` (refus de tout cycle, même en SQL direct) |
| `brands` | Entité ajoutée à A.6 pour le CRUD des marques d'A-ADM-01. Nom unique **sans tenir compte de la casse** (index unique sur `lower(name)`, comme `users.email`), `slug` unique, désactivation logique (`is_active`) |
| `products` | `sku` unique, noms et descriptions FR/EN, `price_cents` BIGINT ≥ 0, `specs` JSONB (objet), `brand_id` et `category_id` (RESTRICT), `is_active`, `created_at`, `updated_at`, `search_vector` généré |
| `product_images` | URL `https://` (CHECK), textes alternatifs FR/EN, `position` unique par produit |
| `inventory` | Clé (`product_id`, `store_id`), CHECK `on_hand >= 0`, `reserved >= 0`, `reserved <= on_hand`, `reorder_threshold >= 0`, `version >= 1` |
| `stock_movements` | Quantité **signée** (signe contrôlé par type), types contrôlés, motif obligatoire pour `adjustment`, clé étrangère composée vers `inventory`, `actor_id`, `order_id`. **Ajout seulement** : un déclencheur refuse UPDATE et DELETE |
| `carts`, `cart_items` | Un panier par client, magasin de cueillette, quantité de 1 à 20, une ligne par produit |
| `orders`, `order_items`, `order_status_history` | Statuts d'A-ORD-07 (CHECK), montants en cents, `total = sous-total − remise + TPS + TVQ` (CHECK), instantané du nom et du prix, historique des transitions |
| `payment_events` | `stripe_event_id` en clé primaire (idempotence des webhooks) |

Les produits et les marques ne sont **jamais supprimés** : ils sont désactivés.

## 3. Recherche plein texte (A-CAT-03)

La migration crée deux configurations de recherche, copies de `french` et `english`, dans lesquelles
le dictionnaire `unaccent` est appliqué **avant** la racinisation :

```sql
CREATE TEXT SEARCH CONFIGURATION public.fr_unaccent (COPY = pg_catalog.french);
ALTER TEXT SEARCH CONFIGURATION public.fr_unaccent
    ALTER MAPPING FOR hword, hword_part, word WITH public.unaccent, pg_catalog.french_stem;
```

`products.search_vector` est une colonne **générée** (`GENERATED ALWAYS AS … STORED`) : noms FR et EN
(poids A) et descriptions FR et EN (poids C). L'index est un GIN. La requête combine les deux langues :
`websearch_to_tsquery('fr_unaccent', q) || websearch_to_tsquery('en_unaccent', q)`, triée par
`ts_rank_cd`.

**Décision (option A′, validée par un essai isolé avant la migration)** : `to_tsvector(regconfig, text)`
est `IMMUTABLE`, donc accepté dans une colonne générée, sans fonction enveloppe. Limites connues :

- Une colonne générée ne peut pas lire une autre table : le nom de la **marque** n'est pas dans le
  vecteur (le filtre par marque utilise `brand_id`).
- PostgreSQL 16 ne permet pas de modifier l'expression d'une colonne générée : changer la formule
  demande de supprimer puis recréer la colonne et son index.
- Alembic ne compare pas l'expression : un test compare l'expression réellement présente en base à
  celle du modèle (`SEARCH_VECTOR_SQL`).
- Si les règles d'`unaccent` changeaient (mise à jour de l'extension), un `UPDATE` des lignes
  recalcule les vecteurs.

Critères vérifiés par les tests : « perceuse », « perceuses », « drill » et « drills » trouvent les
perceuses ; « equerre », « équerre » et « ÉQUERRE » trouvent les équerres ; un terme inconnu, une
requête de mots vides anglais (« the and of ») ou des caractères spéciaux (`'; DROP TABLE …`,
`a & b | !c`) renvoient une liste vide, sans erreur (paramètres liés, `websearch_to_tsquery`).

Comportements observés à connaître :

- La racinisation élargit les résultats : « drill » trouve aussi les forets (« drill bit set ») et les
  ancrages « self-drilling » ; « perceuse » trouve aussi les forets (« pour perceuse »).
- La configuration `french` de PostgreSQL, reprise telle quelle, ne traite pas « les » comme un mot
  vide : une recherche « le la les » peut donc renvoyer des produits dont la description contient « les ».

## 4. Stocks

- **Écriture** : `inventory_service.record_movement` verrouille la ligne (`SELECT … FOR UPDATE`),
  ajoute le mouvement et met à jour `on_hand` dans la même transaction. L'amorçage crée les lignes
  neuves en lot avec `create_initial_stock` (ligne d'inventaire + mouvement `receipt` dans la même
  transaction).
- **Invariant L1** : `on_hand` = somme des quantités des mouvements physiques (`receipt`, `sale`,
  `adjustment`, `return`, `transfer_in`, `transfer_out`). `find_discrepancies` liste les écarts.
- `reservation` et `release` (qui touchent `reserved`) sont définis et contrôlés en SQL, mais leur
  enregistrement par le service est refusé jusqu'au L2 (réservations des commandes, ADR-001).
- `TRUNCATE` n'est pas bloqué par le déclencheur : c'est une opération d'administration, utilisée par
  la suite de tests pour vider la base entre deux tests.

**Disponibilité publique (A-CAT-02)**, calculée à chaque lecture et jamais stockée :

| Statut | Règle (disponible = `on_hand − reserved`) |
|---|---|
| `out_of_stock` (Rupture) | disponible ≤ 0, ou aucune ligne d'inventaire |
| `low_stock` (Stock faible) | 0 < disponible ≤ `reorder_threshold` |
| `in_stock` (En stock) | disponible > `reorder_threshold` |

Les quantités ne sont jamais renvoyées par l'API publique.

## 5. Routes

Publiques (sans authentification ; 120 requêtes par minute et par adresse IP, puis 429
`rate_limited` avec `Retry-After` ; en-têtes `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`
hérités du middleware de l'API) :

| Route | Exigence | Détails |
|---|---|---|
| `GET /api/v1/categories` | A-CAT-01 | Arbre complet (`children`), FR/EN |
| `GET /api/v1/stores` | A-CAT-02 | Magasins et heures d'ouverture |
| `GET /api/v1/products` | A-CAT-01 | `page` (≥ 1), `size` (1 à **50**, 20 par défaut), `sort` (`newest`, `price_asc`, `price_desc`, `name_asc`, `name_desc`), `lang` (tri par nom), `category_id` (sous-catégories incluses), `brand_id` |
| `GET /api/v1/products/{id}` | A-CAT-02 | Fiche FR/EN, SKU, prix, images, caractéristiques, disponibilité |
| `GET /api/v1/products/{id}/availability` | A-CAT-02 | Statut par magasin |
| `GET /api/v1/search?q=` | A-CAT-03 | `q` de 1 à 100 caractères, `page`, `size` |

Administration (`/api/v1/admin`, rôle **administrateur** et MFA complétée ; 401 sans jeton, 403 sinon) :

| Route | Effet |
|---|---|
| `GET`, `POST /products` · `GET`, `PATCH`, `DELETE /products/{id}` | Liste (filtre `is_active`), création (201), consultation, modification partielle, désactivation (204) |
| `POST /products/{id}/images` · `DELETE /products/{id}/images/{image_id}` | Image par URL `https://` (sans identifiants, hôte valide, ≤ 500 caractères) |
| `GET`, `POST /categories` · `PATCH`, `DELETE /categories/{id}` | Suppression refusée (409) si la catégorie a des sous-catégories ou des produits ; cycle refusé (422) |
| `GET`, `POST /brands` · `PATCH`, `DELETE /brands/{id}` | `DELETE` désactive la marque ; une marque désactivée ne peut plus être attribuée (422) |

Erreurs : 401, 403, 404 (`product_not_found`, `category_not_found`, `brand_not_found`, `image_not_found`),
409 (`sku_taken`, `slug_taken`, `brand_name_taken`, `image_position_taken`, `category_has_children`,
`category_in_use`), 422 (validation, `category_cycle`, `brand_inactive`, `query_blank`). Le format est
celui de l'API (`{"detail": {"code", "message"}}`) ; le passage au format `ErrorOut` du contrat est
prévu dans un sous-lot séparé (0.A).

**PATCH** : un champ absent n'est pas modifié ; `null` efface un champ facultatif (`description_*`,
`brand_id`, `category_id`) ; `null` sur un champ obligatoire est refusé (422).

## 6. Données d'amorçage

`python -m app.seed.seed_l1` (depuis `api/`, après `alembic upgrade head`) :

| Élément | Volume |
|---|---|
| Magasins | 3 (Saint-Jérôme, Sainte-Agathe-des-Monts, Mont-Tremblant) |
| Catégories | 30, sur trois niveaux |
| Marques | 8 (fictives) |
| Produits | 157, bilingues, avec SKU, prix, descriptions, caractéristiques et une image |
| Lignes d'inventaire | 471 (chaque produit dans chaque magasin) : 56 ruptures, 71 stocks faibles, 344 en stock |
| Mouvements `receipt` | 415, un par ligne dont le stock de départ est positif (11 702 unités au total) |

- **Idempotent** : identifiants déterministes (UUID v5) et clés naturelles ; une relance ne crée rien
  et ne modifie pas les changements faits par un administrateur.
- **Déterministe** : les quantités dérivent du SKU et du magasin (environ 15 % de ruptures et 15 % de
  stocks faibles, pour démontrer les trois statuts).
- **Sans données réelles** : marques, adresses et téléphones (555) fictifs ; images sur le domaine
  réservé `.example`.
- Refus si `APP_ENV=production`, sauf avec `--allow-production`.

## 7. Écarts et limites connues

- Les images sont désignées par une URL `https://` ; le téléversement de fichiers (`multipart`, contrôle
  du type et de la taille) attend la décision sur le stockage externe.
- Le format d'erreur `ErrorOut` du contrat (avec `request_id`) n'est pas encore appliqué (sous-lot 0.A).
- Les routes de panier, de commande et de paiement relèvent du L2.
