# Procédure — comptes de démonstration par rôle (cahier §6.3)

> **État au 26 novembre 2026** : les quatre comptes `demo-…@example.com` ont été créés en production
> par le responsable (autorisation écrite), puis vérifiés en lecture seule ; le mot de passe de
> l'administrateur a été réinitialisé seul, avec le même traitement que la réinitialisation par
> courriel (Argon2id, sessions fermées, rôle et MFA inchangés). Aucun mot de passe n'a été écrit
> dans Git, un journal ou une conversation.

Script : `python -m app.seed.demo_accounts` (`api/app/seed/demo_accounts.py`, PR #38).
**Il n'est jamais lancé automatiquement** : ni `render.yaml`, ni un workflow, ni un Dockerfile ne l'appellent.

| Compte | Rôle | Magasin | MFA |
|---|---|---|---|
| `demo-client@<domaine>` | client | — | non |
| `demo-commis@<domaine>` | clerk (commis) | Saint-Jérôme | **obligatoire** à la 1re connexion |
| `demo-gerant@<domaine>` | manager (gérant) | Saint-Jérôme | **obligatoire** |
| `demo-admin@<domaine>` | admin | — | **obligatoire** |

## Garanties (vérifiées par `api/tests/test_demo_accounts.py`)

- Aucun mot de passe dans le code, dans Git, à l'écran ni dans les journaux : ils viennent uniquement de
  `DEMO_PASSWORD_CLIENT`, `DEMO_PASSWORD_COMMIS`, `DEMO_PASSWORD_GERANT`, `DEMO_PASSWORD_ADMIN`.
- Politique A-AUTH-03 appliquée (≥ 12 caractères, pas le nom du compte, pas un mot de passe courant) ;
  hachage Argon2id ; tout ou rien (aucun compte créé si un mot de passe est refusé).
- Idempotent : un compte existant n'est jamais modifié, sauf `--reinitialiser` (qui ferme aussi ses sessions).
- Production refusée sans `--allow-production`.
- Courriel marqué vérifié : aucun fournisseur de courriel n'est nécessaire pour la démonstration.

## A. Vérification locale (sans risque, base de développement)

```bash
cd api
python -m app.seed.seed_l1                 # magasins et produits, si ce n'est pas déjà fait
# Saisir les quatre mots de passe sans les écrire dans un fichier versionné :
read -rs DEMO_PASSWORD_CLIENT && export DEMO_PASSWORD_CLIENT
read -rs DEMO_PASSWORD_COMMIS && export DEMO_PASSWORD_COMMIS
read -rs DEMO_PASSWORD_GERANT && export DEMO_PASSWORD_GERANT
read -rs DEMO_PASSWORD_ADMIN  && export DEMO_PASSWORD_ADMIN
python -m app.seed.demo_accounts --domaine example.com
```

La sortie n'affiche que le rôle, l'adresse et l'état (`créé`, `existant`, `réinitialisé`).

## B. Production (Neon) — **uniquement avec l'autorisation explicite du responsable**

1. Choisir quatre mots de passe longs dans un gestionnaire de mots de passe, et un domaine d'adresses
   (p. ex. `example.com`, qui ne reçoit pas de courriel).
2. Sur un poste de confiance, ouvrir un terminal **sans historique partagé**, puis définir la connexion
   Neon **en la saisissant** (jamais dans un fichier du dépôt) :
   `read -rs DATABASE_URL && export DATABASE_URL` (valeur : chaîne de connexion Neon, `sslmode=require`).
3. Définir les variables exigées par la validation de la configuration. Le script n'émet aucun jeton et
   ne chiffre rien : des valeurs **jetables**, générées pour cette seule exécution, suffisent (ne pas
   réutiliser celles de Render) :
   ```bash
   export APP_ENV=production EMAIL_BACKEND=disabled
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
   export MFA_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
   ```
4. Saisir les quatre `DEMO_PASSWORD_*` comme en A, puis :
   `python -m app.seed.demo_accounts --domaine example.com --allow-production`.
5. Fermer le terminal (`unset DATABASE_URL DEMO_PASSWORD_CLIENT DEMO_PASSWORD_COMMIS DEMO_PASSWORD_GERANT DEMO_PASSWORD_ADMIN`).
6. Transmettre les identifiants **en privé** au responsable du projet (jamais dans le README, une issue ou une PR).

## C. Vérification après création (production, sans modification)

| Vérification | Comment | Attendu |
|---|---|---|
| Client | Connexion sur `/connexion` du site (PR #50) | Page « Mon compte », rôle « Client » |
| Personnel sans MFA | Connexion du commis | `mfa_setup_required` : message « authentification multifacteur requise » |
| MFA | `POST /api/v1/auth/mfa/setup` puis `/mfa/enable` depuis `/docs`, avec une application TOTP | Connexion suivante en deux étapes |
| Administration | Après MFA, `GET /api/v1/admin/products` depuis `/docs` | 200 ; avant la MFA : 403 `mfa_required` |
| Rôles | Le client appelle `/api/v1/admin/products` | 403 |
| Journaux | Render → Logs | Aucun mot de passe ni jeton |
