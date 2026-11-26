# Registre des preuves — L1 v0.1.0

Ce registre distingue trois niveaux de preuve, sans jamais les confondre :

- **Technique** : constat reproductible par un tiers (CI GitHub, requête HTTP publique, test automatisé).
- **Déclaré** : test réel effectué par le responsable du projet et déclaré par écrit ; il devient une
  preuve archivée quand la capture correspondante est déposée.
- **À fournir** : aucune preuve n'existe encore.

**Aucune capture n'a été produite par l'outillage.** Les captures sont à déposer par le responsable,
sans secret ni donnée personnelle (masquer les adresses courriel réelles), par exemple dans
`docs/preuves/` ou en pièce jointe de l'issue concernée.

Relevé du **26 novembre 2026**, `main` = `a8d88cf`.

| Id | Preuve | Exigence | Niveau actuel | Ce qui existe | À fournir |
|---|---|---|---|---|---|
| P1 | Migrations appliquées en production | Artéfact 3 | Technique | La commande de démarrage Render enchaîne `alembic upgrade head && …` ; le déploiement de `a8d88cf` a réussi, donc les migrations ont été appliquées (un échec arrête le démarrage) | Capture du journal Render montrant `alembic upgrade head` (complément) |
| P2 | Site web : catalogue, fiche, recherche, bascule FR/EN | A-CAT-01 à 03, ENF-10 | Technique (HTTP) | Pages en 200 ; recherche « perceuse » 13, « drill » 14, « equerre » = « équerre » 5 | Captures de la démonstration W1 à W5 |
| P3 | Documentation de l'API `/docs` | Artéfact 5 | Technique | `docs/api/openapi-l1.json` identique à `/openapi.json` de production (28 chemins, 35 schémas) | Capture de `/docs` (facultative) |
| P4 | Mobile connecté à l'API en ligne | A.11 | Technique | Test d'intégration contre l'API de production : 13 tests réussis (26 novembre) | Captures M1 à M6 sur un appareil ou un émulateur |
| P5 | Bureau connecté à l'API en ligne | A.11 | Technique | Test d'intégration contre l'API de production : 21 tests réussis (26 novembre) ; paquet `desktop-release` | Captures B1 à B4 |
| P6 | Courriels réels (Brevo) | A-AUTH-01, A-AUTH-04 | **Déclaré (A-AUTH-04 seulement)** | Réinitialisation du mot de passe réussie selon le responsable ; API démarrée avec la configuration Brevo | **A-AUTH-01 (vérification à l'inscription) à tester** ; captures des deux courriels, des pages d'arrivée et du journal Brevo (« Delivered ») |
| P7 | Tableau GitHub Projects | Artéfact 8 | Technique | 70 éléments, sans doublon ; issues fermées en « Done » | Capture après saisie des sprints, responsables et heures |
| P8 | Données réelles de l'équipe | Artéfact 8 | **À fournir** | Gabarits seulement | `donnees-equipe-a-completer.md` rempli |
| P9 | Procès-verbal d'approbation signé | Remise | **À fournir** | `proces-verbal-approbation-l1.md` (non signé) | Signature |
| P10 | Administration et images (C1 à C8) | A-ADM-01 | Technique + déclaré | Production : image Cloudinary servie (200, `image/jpeg`) en image principale du produit ADHE-COLB ; routes d'administration en 401 sans jeton ; C2 à C8 réussis selon le responsable | Captures C2 à C8 |
| P11 | Comptes de démonstration et MFA | §6.3, A-AUTH-05, A-AUTH-06 | Déclaré | Quatre comptes vérifiés (lecture seule) et MFA de l'administrateur activée selon le responsable ; procédure répétée sur une base de test isolée | Capture de la connexion de chaque rôle (sans mot de passe) |

## Questions ouvertes

- **Produit ADHE-COLB** : il porte encore une image Cloudinary en position 0, téléversée le
  2026-11-26 à 20:57 UTC. Le responsable indique avoir retiré l'image de test (C8). Il doit confirmer
  si cette image est voulue ; sinon, la retirer depuis `/admin`. Elle n'a pas été supprimée par l'outillage.
