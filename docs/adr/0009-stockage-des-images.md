# ADR-009 — Stockage persistant des images de produits

- **Statut :** Proposé (22 novembre 2026) — **en attente de l'accord du responsable du projet** pour le choix et l'activation du fournisseur.
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
2. **Fournisseur (à activer après accord) :** Cloudinary, par son API HTTPS d'envoi signé (aucune
   nouvelle dépendance Python), avec les secrets `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` et
   `CLOUDINARY_API_SECRET` saisis **uniquement** dans le tableau de bord de Render.

## Conséquences

- Tant que le fournisseur n'est pas activé, A-ADM-01 est **partiel en production** : les images
  restent désignées par une URL https ; le téléversement répond 503 avec un message explicite.
- Les URL Cloudinary (`https://res.cloudinary.com/...`) sont compatibles avec la CSP du web
  (`img-src 'self' https: data:`).
- L'interface d'administration (web) qui appellera cette route reste à réaliser.
