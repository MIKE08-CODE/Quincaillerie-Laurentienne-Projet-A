# ADR-009 — Stockage persistant des images de produits

- **Statut :** Proposé (22 novembre 2026) ; adaptateur Cloudinary **implémenté et testé sans réseau** (23 novembre 2026) — **activation en attente de l'accord du responsable** (compte gratuit et secrets dans Render).
- **Exigences :** A-ADM-01 (« téléversement d'images avec validation du type et de la taille »), ENF-03 (sécurité), contrainte de coûts §6.3 (offres gratuites uniquement).

## Contexte

L'API tourne sur l'offre gratuite de Render : son disque est **éphémère** (effacé à chaque déploiement
et à chaque redémarrage). La base Neon gratuite est limitée en taille, et y ranger des images
alourdirait les sauvegardes, les requêtes et la bande passante de la base. Il faut donc un stockage
d'objets externe, gratuit, **sans carte bancaire**, qui renvoie une URL https publique.

## Options étudiées (vérifiées le 22 novembre 2026)

| Option | Gratuit sans carte | Limites | Risques | Verdict |
|---|---|---|---|---|
| **Cloudinary** (offre Free) | Oui, selon sa documentation | ≈ 25 crédits par 30 jours glissants (1 crédit ≈ 1 Go stocké ou 1 Go servi ou 1 000 transformations) | Fournisseur spécialisé : dépendance à son API | **Recommandé** |
| Supabase Storage | Oui | 1 Go stocké, 5 Go de sortie | **Projet mis en pause** après une semaine de faible activité de la base | Écarté (démonstration risquée) |
| Cloudflare R2 | Offre gratuite, mais un moyen de paiement serait demandé avant le premier bucket (guides tiers) | 10 Go-mois | Carte bancaire probable | Écarté (contrainte §6.3) |
| Disque de Render | — | Éphémère | Images perdues à chaque déploiement | Interdit |
| PostgreSQL (`bytea`) | Oui | Quota Neon gratuit | Base alourdie, pas de CDN | Écarté sans justification forte |

Sources : documentation de Cloudinary (offre gratuite sans carte, crédits), FAQ de Supabase sur la
mise en pause des projets gratuits, tarifs et guides de démarrage de Cloudflare R2. Les conditions
des offres gratuites changent : les revérifier avant l'activation.

## Décision proposée

1. **Indépendant du fournisseur (implémenté) :** route `POST /api/v1/admin/products/{id}/images/upload`
   (administrateur avec MFA), corps brut avec `Content-Type: image/jpeg|png|webp` ;
   - type déduit de la **signature des octets** et comparé au type déclaré (SVG, GIF, HTML, PDF,
     exécutables refusés) ;
   - taille maximale `IMAGE_MAX_BYTES` (5 Mio), lue en flux et refusée dès le dépassement (413) ;
   - dimensions lues dans l'en-tête et limitées à `IMAGE_MAX_DIMENSION` (6000 px) contre les bombes
     de décompression ; aucune image n'est décodée côté serveur ;
   - nom de fichier généré par le serveur (`products/<id>/<uuid>.<ext>`), jamais celui du client ;
   - fichier supprimé du stockage si l'écriture en base échoue, et lors du retrait de l'image ;
   - sans fournisseur configuré : **503 `image_storage_not_configured`** (défaut en production).
2. **Fournisseur (implémenté, à activer après accord) :** `CloudinaryStorage` (`api/app/services/image_storage.py`) :
   - envoi signé `multipart/form-data` vers `https://api.cloudinary.com/v1_1/<compte>/image/upload`,
     signature **SHA-256** des paramètres triés suivis du secret (format vérifié par l'exemple officiel
     de la documentation de Cloudinary) ; aucune nouvelle dépendance Python ;
   - garde-fous côté Cloudinary : `allowed_formats=jpg,png,webp`, `overwrite=false`, dossier dédié ;
   - l'URL renvoyée n'est acceptée que si elle est en https et appartient au compte configuré ;
   - suppression signée (`destroy`, `invalidate=true`) lors du retrait de l'image ou d'un échec en base ;
     les URL externes ne sont jamais touchées ;
   - erreurs du fournisseur → 503 `image_storage_unavailable`, sans secret dans le message ni les journaux ;
   - configuration incomplète (`IMAGE_STORAGE_BACKEND=cloudinary` sans les trois identifiants) : **l'API
     refuse de démarrer**.

   **Variables à saisir dans Render (uniquement par le responsable) :**

   | Variable | Valeur | Secret |
   |---|---|---|
   | `IMAGE_STORAGE_BACKEND` | `cloudinary` | Non |
   | `CLOUDINARY_CLOUD_NAME` | nom du compte (tableau de bord Cloudinary) | Non |
   | `CLOUDINARY_API_KEY` | clé d'API | Non (mais à ne pas publier) |
   | `CLOUDINARY_API_SECRET` | secret d'API | **Oui** |
   | `CLOUDINARY_FOLDER` | `quincaillerie-laurentienne` (défaut) | Non |

   **Test réel à faire après activation :** administrateur avec MFA → `POST
   /api/v1/admin/products/{id}/images/upload` (depuis `/docs` ou la page d'administration web) avec un
   JPEG → 201 et une URL `https://res.cloudinary.com/...` ; l'image s'affiche sur la fiche du site ;
   `DELETE .../images/{image_id}` → l'image disparaît aussi du tableau de bord Cloudinary.

## Conséquences

- Tant que le fournisseur n'est pas activé, A-ADM-01 est **partiel en production** : les images
  restent désignées par une URL https ; le téléversement répond 503 avec un message explicite.
- Les URL Cloudinary (`https://res.cloudinary.com/...`) sont compatibles avec la CSP du web
  (`img-src 'self' https: data:`).
- L'interface d'administration (web) qui appellera cette route reste à réaliser.
