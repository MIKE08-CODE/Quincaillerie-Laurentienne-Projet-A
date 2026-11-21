# Notes de version — v0.1.0 (L1 — Fondations) — BROUILLON

**Non publiées.** L'étiquette `v0.1.0` n'existe pas : elle sera créée après la fusion des PR et le
déploiement, sur autorisation. Les éléments marqués « en PR » ne sont pas encore sur `main`.

## Nouveautés

### API (FastAPI, Python 3.11)
- Comptes et authentification : inscription avec consentement, vérification du courriel, connexion
  (JWT 15 min + cookie de rafraîchissement httpOnly), politique de mot de passe et Argon2id,
  réinitialisation, rôles et affectation au magasin, verrouillage progressif, MFA TOTP du personnel
  (A-AUTH-01 à 07) — *fusionné*.
- Catalogue public : catégories, magasins, produits paginés (≤ 50) avec tris et filtres, fiche produit
  bilingue, disponibilité calculée par magasin, recherche plein texte FR/EN sans accents
  (A-CAT-01 à 03) — *en PR #29*.
- Administration du catalogue : produits (création, PATCH, désactivation, images par URL), catégories
  et marques (A-ADM-01) — *en PR #29*.
- Migrations de toutes les entités Must ; amorçage de démonstration (3 magasins, 157 produits, stocks)
  — *en PR #29*.

### Clients
- Web React 18 : accueil, catalogue, recherche, fiche produit, magasins — *en PR #30*.
- Mobile Expo : liste des produits et navigation par catégorie — *en PR #31*.
- Bureau WPF : liste des produits et recherche — *en PR #32*.

### DevOps
- Protection de `main`, `api-ci`, `security` (CodeQL, Gitleaks), Dependabot — *fusionné*.
- `web-ci`, `mobile-ci`, `desktop-ci` — *en PR #30 à #32*.
- README d'installation et procédure de déploiement — *en PR #33*.

## Limitations connues
- **Non déployé** à ce jour (URL à compléter).
- Envoi de courriels absent en production (inscription et réinitialisation).
- Format d'erreur `ErrorOut` du contrat non encore appliqué (ADR-008).
- Images désignées par URL ; pas de téléversement de fichiers.
- Interface web d'administration non réalisée (API seulement).

## Migrations
Head Alembic : `e2c9a4b7d3f1`. Appliquer `alembic upgrade head`, puis `python -m app.seed.seed_l1`.

## URL
API : à compléter · Web : à compléter · Vidéo de démonstration : à compléter.
