# Document de vision et d’exigences

**Projet A — Quincaillerie Laurentienne | Plateforme de commerce omnicanal**

> **Livrable :** L1 — Fondations (semaine 3)  
> **Version documentaire :** 1.2 — révision du 21 novembre 2026  
> **Équipe :** [à compléter]  
> **Responsable :** [à compléter]  
> **Dépôt GitHub :** https://github.com/MIKE08-CODE/Quincaillerie-Laurentienne-Projet-A  
> **Statut :** version révisée pour revue — validation du responsable en attente

## Historique et contrôle documentaire

| Version | Date | Nature de la révision | Validation |
|---|---|---|---|
| 1.0 | 18 novembre 2026 | Document initial de vision et d’exigences | Proposition |
| 1.1 | 19 novembre 2026 | Révision de travail : reformulation des récits et séparation des critères complémentaires | Non attestée |
| 1.2 | 21 novembre 2026 | Corrections linguistiques, périmètre L1, traçabilité, critères mesurables, échéances et références | En attente |

**Auteur(s), équipe, approbateur et date de signature :** à renseigner. Ce document est un support de validation, pas une attestation de réception du logiciel.

## 1. Objet, références et méthode

Ce document formalise la vision du projet, son périmètre, les acteurs, les objectifs mesurables et le carnet de produit. Il reprend les exigences du cahier des charges RCW, version 1.0 (octobre 2026), Partie I, Partie II — Projet A, Partie IV et annexe A. Les identifiants A-* et ENF-* sont conservés. Les récits utilisateurs constituent une reformulation de travail et ne remplacent pas les exigences officielles.

Les récits utilisateurs reformulent les exigences officielles sans modifier leur priorité. Les critères additionnels proposés pour faciliter les tests sont **à valider par l’équipe**. Les liens GitHub ne sont pas inventés : ils doivent être ajoutés après création des issues.

**Priorités MoSCoW :** **Must** (indispensable), **Should** (souhaitable), **Could** (optionnel), **Won’t** (exclu du périmètre de la présente livraison ou du projet, selon indication explicite). La priorité ne détermine pas à elle seule le jalon de livraison.

## 2. Contexte et problèmes

Quincaillerie Laurentienne est une chaîne familiale fictive fondée en 1978, exploitant trois magasins à Saint-Jérôme, Sainte-Agathe-des-Monts et Mont-Tremblant, avec environ 70 employés et 4 000 produits (outils, quincaillerie, plomberie, électricité, peinture, jardinage, saisonnier). Son site est statique, sans vente en ligne; les stocks sont gérés dans un logiciel de bureau ancien, non partagé entre magasins.

- Absence de vente en ligne et perte de clientèle face aux grands détaillants.
- Stocks non synchronisés, risques de disponibilité erronée et de survente.
- Cueillette improvisée, attente, commandes perdues ou remises à la mauvaise personne.
- Questions répétitives mobilisant les employés.
- Manque de rapports de vente pour orienter les décisions.

## 3. Vision du produit

Offrir une plateforme omnicanale bilingue et sécurisée reliant les trois magasins : catalogue et achat en ligne avec cueillette, visibilité fiable des stocks, gestion des commandes et des réceptions par le personnel, administration centralisée et « Conseiller Laurentien » fondé sur une base documentaire approuvée. Le serveur applique les règles d’affaires pour tous les clients web, mobile et bureau.

## 4. Objectifs et indicateurs de réussite

| Objectif | Indicateur de réussite |
|---|---|
| Boutique bilingue et paiement sécurisé | Trouver un produit, payer en mode test et recevoir confirmation en moins de 3 minutes. |
| Intégrité des stocks | Aucune survente lors d’un test de 50 acheteurs simultanés sur les dernières unités. |
| Cueillette sûre et rapide | Validation par QR en moins de 30 secondes, sans remise au mauvais client. |
| Réponses aux questions fréquentes | Assistant RAG : au moins 80 % de réponses correctes avec citations. |
| Pilotage commercial | Tableau de bord : ventes par magasin, meilleurs produits et ruptures imminentes. |

## 5. Parties prenantes et permissions

| Acteur | Besoins et responsabilités |
|---|---|
| Visiteur | Catalogue, disponibilité, assistant, inscription. |
| Client | Panier, paiement, historique, QR, profil, droits sur les données. |
| Commis | Stocks de son magasin, préparation, cueillette, retours. |
| Gérant | Fonctions commis, réception, approbations, rapports du magasin. |
| Administrateur | Produits, prix, promotions, rôles, rapports globaux, base de connaissances. |
| Stripe (système externe) | Notifications de paiement par webhook signé. |
| Responsable du projet | Validation de la portée, arbitrages et acceptation des livrables. |

## 6. Portée

### 6.1 Inclus

Boutique web; catalogue, recherche, compte, panier, paiement test, historique; cueillette dans trois magasins; application mobile client; application de bureau du personnel; administration et rapports; agent RAG; sécurité, confidentialité (Loi 25), tests, CI/CD et déploiement.

### 6.2 Exclus ou optionnels

Livraison à domicile et transporteurs; paiements réels; intégration au système comptable ou au logiciel existant; bons de commande fournisseurs; programme de fidélité. Les trois derniers éléments, ainsi que la livraison, peuvent relever d’objectifs optionnels, non de la portée obligatoire.

**Distinction :** les exclusions sont des éléments *Won’t* pour la portée obligatoire actuelle; les fonctionnalités expressément optionnelles restent à arbitrer sans devenir des engagements de livraison.

## 7. Parcours métiers majeurs

- Achat : consulter → choisir magasin → panier → validation serveur → réservation de stock (15 min) → Stripe test → webhook vérifié → commande payée.
- Préparation et cueillette : commande payée → préparation par le commis → commande prête → QR signé → validation dans le bon magasin → statut picked_up, jeton invalidé.
- Stock : réception / ajustement / vente / réservation / libération → mouvement auditable par produit et magasin.
- Assistance : question FR/EN → récupération de documents approuvés → réponse avec sources ou refus si contexte insuffisant.

## 8. Carnet de produit — récits utilisateurs et critères d’acceptation

**Convention :** chaque fiche indique l’identifiant du cahier, un identifiant US, la priorité MoSCoW, le récit, les critères officiels et les critères complémentaires proposés, puis le lien GitHub à compléter. Les critères complémentaires ne sont pas présentés comme des obligations déjà validées.

**Traçabilité GitHub :** chaque issue devra reprendre l’identifiant `A-*`, la priorité, les critères, le jalon, un responsable et le lien vers la PR/test. Le dépôt est identifié, mais la correspondance entre chaque exigence et ses issues n’a pas été auditée : les liens restent **à identifier / relier**, sans création fictive.


### 8.1 Comptes et authentification


#### US-001 — A-AUTH-01 · Must

**Récit utilisateur :** En tant que visiteur, je veux créer un compte et vérifier mon adresse courriel, afin de commander et suivre mes achats.

**Exigence source :** Inscription du client avec courriel, mot de passe, nom, langue préférée et consentement explicite à la politique de confidentialité. Lien de vérification du courriel requis avant la première commande.

**Critères d’acceptation :**
- **Critère du cahier :** un compte non vérifié ne peut pas passer de commande; l’horodatage du consentement est enregistré.
- **Critères complémentaires proposés (à valider) :** Les champs nom, courriel, mot de passe et langue sont enregistrés; le consentement est explicite et horodaté; une vérification est envoyée.

**Traçabilité :** `A-AUTH-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-002 — A-AUTH-02 · Must

**Récit utilisateur :** En tant qu’utilisateur inscrit, je veux ouvrir et fermer une session sécurisée, afin d’accéder à mon compte sans exposer mes identifiants.

**Exigence source :** La connexion renvoie un jeton d’accès de courte durée (≤ 15 min) et un jeton de rafraîchissement dans un témoin httpOnly, Secure, SameSite. La déconnexion révoque le jeton de rafraîchissement.

**Critères d’acceptation :**
- **Critère du cahier :** jeton expiré → 401; le rafraîchissement fonctionne; un jeton révoqué est rejeté.
- **Critères complémentaires proposés (à valider) :** La connexion délivre un accès de 15 minutes maximum et un rafraîchissement protégé par cookie httpOnly, Secure et SameSite; la déconnexion révoque le rafraîchissement.

**Traçabilité :** `A-AUTH-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-003 — A-AUTH-03 · Must

**Récit utilisateur :** En tant qu’utilisateur, je veux choisir un mot de passe robuste, afin de protéger mon compte.

**Exigence source :** Politique de mot de passe (min. 12 caractères, vérification contre une liste de mots de passe courants) et hachage Argon2id.

**Critères d’acceptation :**
- **Critère du cahier :** mots de passe faibles refusés avec un message clair; aucun mot de passe en clair dans la BD ou les journaux.
- **Critères complémentaires proposés (à valider) :** Les mots de passe de moins de 12 caractères ou courants sont refusés; les mots de passe sont hachés avec Argon2id.

**Traçabilité :** `A-AUTH-03` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-004 — A-AUTH-04 · Must

**Récit utilisateur :** En tant que client, je veux réinitialiser mon mot de passe par courriel, afin de retrouver l’accès à mon compte.

**Exigence source :** Réinitialisation du mot de passe par jeton à usage unique et limité dans le temps (30 min) envoyé par courriel. Réponse identique que le courriel existe ou non.

**Critères d’acceptation :**
- **Critère du cahier :** la réutilisation du jeton échoue; aucune énumération d’utilisateurs.
- **Critères complémentaires proposés (à valider) :** Le lien expire après 30 minutes et ne fonctionne qu’une fois; le message affiché ne révèle pas l’existence du compte.

**Traçabilité :** `A-AUTH-04` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-005 — A-AUTH-05 · Must

**Récit utilisateur :** En tant qu’administrateur, je veux attribuer des rôles et des magasins aux membres du personnel, afin de limiter chaque accès aux opérations autorisées.

**Exigence source :** Contrôle d’accès basé sur les rôles (visiteur, client, commis, gérant, administrateur) avec affectation du personnel à un magasin.

**Critères d’acceptation :**
- **Critère du cahier :** tests automatisés pour chaque rôle sur chaque point de terminaison protégé.
- **Critères complémentaires proposés (à valider) :** Les cinq rôles sont pris en charge; les opérations interdites retournent un refus; un commis ne peut pas agir pour un autre magasin.

**Traçabilité :** `A-AUTH-05` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-006 — A-AUTH-06 · Should

**Récit utilisateur :** En tant qu’employé, je veux confirmer mon identité avec un second facteur TOTP, afin de sécuriser les accès du personnel.

**Exigence source :** Authentification multifacteur TOTP obligatoire pour le personnel et les administrateurs.

**Critères d’acceptation :**
- **Critère du cahier :** le personnel ne peut pas accéder aux points de terminaison protégés sans avoir complété la MFA.
- **Critères complémentaires proposés (à valider) :** Une session du personnel sans second facteur validé ne peut pas utiliser les routes protégées.

**Traçabilité :** `A-AUTH-06` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-007 — A-AUTH-07 · Must

**Récit utilisateur :** En tant qu’administrateur, je veux limiter les tentatives de connexion répétées, afin de réduire les attaques par force brute.

**Exigence source :** Limitation de débit et verrouillage progressif à la connexion (p. ex. 5 échecs → blocage de 15 min).

**Critères d’acceptation :**
- **Critère du cahier :** démontré par un script de test.
- **Critères complémentaires proposés (à valider) :** Un script simule cinq échecs successifs et vérifie le blocage ou délai progressif prévu.

**Traçabilité :** `A-AUTH-07` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-008 — A-AUTH-08 · Could

**Récit utilisateur :** En tant que client, je veux me connecter avec Google, afin d’éviter de créer un mot de passe supplémentaire.

**Exigence source :** Connexion avec Google (OAuth 2.0 / OpenID Connect) pour les clients.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Un compte Google valide permet une connexion OIDC; un jeton invalide est refusé.

**Traçabilité :** `A-AUTH-08` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.2 Catalogue et recherche


#### US-009 — A-CAT-01 · Must

**Récit utilisateur :** En tant que visiteur, je veux parcourir les produits par catégorie et les trier, afin de trouver facilement un article.

**Exigence source :** Liste des produits paginée, arborescence de catégories (p. ex. Outils > Outils électriques > Perceuses), tri par prix, nom ou nouveauté.

**Critères d’acceptation :**
- **Critère du cahier :** listes paginées (max. 50 par page); navigation par catégorie fonctionnelle sur le web et le mobile.
- **Critères complémentaires proposés (à valider) :** La pagination est limitée à 50 produits par page; le tri par prix, nom et nouveauté et la navigation par catégories fonctionnent.

**Traçabilité :** `A-CAT-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-010 — A-CAT-02 · Must

**Récit utilisateur :** En tant que client, je veux consulter la fiche et le stock d’un produit par magasin, afin de choisir un article disponible.

**Exigence source :** Fiche produit : nom et description bilingues, code SKU, prix, images, caractéristiques techniques (JSONB), disponibilité par magasin (« En stock », « Stock faible », « Rupture »).

**Critères d’acceptation :**
- **Critère du cahier :** la disponibilité est calculée à partir des stocks réels, pas stockée comme texte.
- **Critères complémentaires proposés (à valider) :** La fiche affiche nom et description FR/EN, SKU, prix, images et caractéristiques; le statut de stock est calculé depuis les quantités.

**Traçabilité :** `A-CAT-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-011 — A-CAT-03 · Must

**Récit utilisateur :** En tant que visiteur, je veux rechercher des articles en français ou en anglais, afin de retrouver un produit même sans connaître son libellé exact.

**Exigence source :** Recherche plein texte en français et en anglais (tsvector PostgreSQL avec configurations française et anglaise), insensible aux accents (unaccent).

**Critères d’acceptation :**
- **Critère du cahier :** « perceuse » et « drill » trouvent les perceuses; « equerre » trouve « équerre ».
- **Critères complémentaires proposés (à valider) :** Les recherches « perceuse » et « drill » retrouvent les perceuses; « equerre » retrouve « équerre ». 

**Traçabilité :** `A-CAT-03` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-012 — A-CAT-04 · Should

**Récit utilisateur :** En tant que client, je veux filtrer les produits par prix, marque et magasin, afin de réduire les résultats aux articles pertinents.

**Exigence source :** Filtres : fourchette de prix, marque, disponibilité dans un magasin choisi.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les filtres de prix, de marque et de disponibilité par magasin modifient correctement les résultats; les filtres combinés fonctionnent.

**Traçabilité :** `A-CAT-04` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-013 — A-CAT-05 · Could

**Récit utilisateur :** En tant que client ayant acheté un produit, je veux publier un avis sur cet article, afin de partager mon expérience avec les autres acheteurs.

**Exigence source :** Avis et évaluations des clients (seulement pour des produits achetés), modérés par l’administrateur avant publication.

**Critères d’acceptation :**
- **Critère du cahier :** un client ne peut pas évaluer un produit jamais acheté; le HTML est échappé.
- **Critères complémentaires proposés (à valider) :** Un achat préalable est requis; les avis restent non publiés avant modération; le HTML affiché est échappé.

**Traçabilité :** `A-CAT-05` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-014 — A-CAT-06 · Could

**Récit utilisateur :** En tant que client, je veux voir des produits souvent achetés ensemble, afin de découvrir des accessoires utiles.

**Exigence source :** Suggestions « Souvent achetés ensemble » basées sur la cooccurrence dans les commandes passées (règles d’association).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les suggestions sont fondées sur des cooccurrences de commandes; en absence de données suffisantes, aucune suggestion trompeuse n’est affichée.

**Traçabilité :** `A-CAT-06` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.3 Panier, commandes et paiement


#### US-015 — A-ORD-01 · Must

**Récit utilisateur :** En tant que client, je veux retrouver mon panier sur plusieurs appareils, afin de continuer mes achats sans perdre ma sélection.

**Exigence source :** Panier conservé côté serveur pour les utilisateurs authentifiés (survit à la déconnexion et au changement d’appareil); panier invité en mémoire locale fusionné à la connexion.

**Critères d’acceptation :**
- **Critère du cahier :** le même panier est visible sur le web et le mobile pour un même compte.
- **Critères complémentaires proposés (à valider) :** Le panier authentifié est conservé côté serveur et partagé entre web et mobile; le panier invité est fusionné à la connexion.

**Traçabilité :** `A-ORD-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-016 — A-ORD-02 · Must

**Récit utilisateur :** En tant que client, je veux choisir un magasin de cueillette et vérifier le stock, afin d’éviter de commander un article indisponible.

**Exigence source :** Le client choisit un magasin de cueillette; le panier valide la disponibilité dans ce magasin et signale clairement les articles non disponibles.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le magasin est sélectionnable; les quantités sont contrôlées pour ce magasin; les indisponibilités sont signalées et bloquent la validation.

**Traçabilité :** `A-ORD-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-017 — A-ORD-03 · Must

**Récit utilisateur :** En tant que client, je veux voir un total exact incluant les taxes et promotions, afin de connaître le montant réel de ma commande.

**Exigence source :** Calcul des prix côté serveur : sous-total, promotions, TPS (5 %) et TVQ (9,975 %), total. Les prix envoyés par le client sont ignorés.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le serveur calcule sous-total, remises, TPS 5 % et TVQ 9,975 %; un prix modifié dans la requête cliente est ignoré.

**Traçabilité :** `A-ORD-03` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-018 — A-ORD-04 · Must

**Récit utilisateur :** En tant que client, je veux réserver temporairement les articles au paiement, afin d’éviter une commande annulée faute de stock.

**Exigence source :** Réservation du stock au paiement dans une transaction avec verrouillage de lignes (`SELECT … FOR UPDATE`) ou verrouillage optimiste par version; la réservation expire après 15 min si le paiement n’est pas complété.

**Critères d’acceptation :**
- **Critère du cahier :** test de charge avec 50 acheteurs simultanés pour 5 unités → exactement 5 commandes réussies.
- **Critères complémentaires proposés (à valider) :** La réservation est atomique et expire après 15 minutes sans paiement; avec 50 acheteurs pour 5 unités, cinq commandes au maximum réussissent.

**Traçabilité :** `A-ORD-04` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-019 — A-ORD-05 · Must

**Récit utilisateur :** En tant que client, je veux payer ma commande en mode test, afin de recevoir une confirmation fiable.

**Exigence source :** Paiement avec Stripe Checkout ou Payment Intents (mode test). Commande confirmée seulement après réception d’un webhook vérifié (`payment_intent.succeeded` / `checkout.session.completed`) avec validation de la signature.

**Critères d’acceptation :**
- **Critère du cahier :** un webhook falsifié sans signature valide est rejeté.
- **Critères complémentaires proposés (à valider) :** Stripe est utilisé en mode test; seule la réception d’un webhook à signature valide permet de confirmer le paiement.

**Traçabilité :** `A-ORD-05` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-020 — A-ORD-06 · Must

**Récit utilisateur :** En tant qu’administrateur, je veux traiter une seule fois chaque événement de paiement, afin d’éviter les doublons de commandes et de déductions de stock.

**Exigence source :** Traitement idempotent des webhooks (identifiants d’événements Stripe enregistrés); les événements en double ne créent ni commande en double ni double déduction de stock.

**Critères d’acceptation :**
- **Critère du cahier :** rejouer le même événement deux fois → une seule commande.
- **Critères complémentaires proposés (à valider) :** Deux envois du même événement Stripe ne créent qu’un effet métier; l’identifiant d’événement est mémorisé.

**Traçabilité :** `A-ORD-06` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-021 — A-ORD-07 · Must

**Récit utilisateur :** En tant que client, je veux suivre les étapes de traitement de ma commande, afin de savoir quand venir la chercher.

**Exigence source :** Machine à états de la commande : `pending_payment → paid → preparing → ready_for_pickup → picked_up`; plus `cancelled`, `refunded`, `expired`. Transitions invalides refusées; chaque transition est horodatée avec son auteur.

**Critères d’acceptation :**
- **Critère du cahier :** tests unitaires pour toutes les transitions valides et invalides.
- **Critères complémentaires proposés (à valider) :** Les états prévus sont respectés; toute transition interdite est rejetée; l’auteur et l’heure de chaque changement sont conservés.

**Traçabilité :** `A-ORD-07` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-022 — A-ORD-08 · Should

**Récit utilisateur :** En tant que client, je veux recevoir des courriels de suivi de commande, afin de être informé sans devoir consulter le site.

**Exigence source :** Courriel de confirmation avec numéro et résumé de commande; courriel lorsque la commande est prête pour la cueillette.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Un courriel contenant le numéro et le résumé suit la confirmation; un autre est envoyé quand la commande est prête.

**Traçabilité :** `A-ORD-08` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-023 — A-ORD-09 · Should

**Récit utilisateur :** En tant que client, je veux annuler une commande avant sa préparation, afin de récupérer mon paiement et libérer les articles.

**Exigence source :** Annulation par le client avant la préparation → remboursement Stripe (test) et libération du stock.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** L’annulation client est possible à l’état paid seulement; le remboursement test est déclenché et le stock libéré.

**Traçabilité :** `A-ORD-09` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-024 — A-ORD-10 · Could

**Récit utilisateur :** En tant qu’administrateur, je veux configurer des promotions limitées dans le temps, afin de proposer des réductions contrôlées.

**Exigence source :** Promotions : pourcentage ou montant fixe, par produit ou catégorie, avec dates de début et de fin; codes promotionnels avec limite d’utilisation.

**Critères d’acceptation :**
- **Critère du cahier :** un code limité à 100 utilisations ne peut pas être utilisé une 101e fois, même en concurrence.
- **Critères complémentaires proposés (à valider) :** Les remises et dates sont respectées; un code limité à 100 usages ne peut pas être utilisé une 101e fois, même en concurrence.

**Traçabilité :** `A-ORD-10` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.4 Cueillette en magasin


#### US-025 — A-PCK-01 · Must

**Récit utilisateur :** En tant que client, je veux recevoir un code QR de cueillette sécurisé, afin de récupérer ma commande en magasin.

**Exigence source :** Lorsqu’une commande passe à `ready_for_pickup`, le système génère un jeton de cueillette signé (p. ex. HMAC ou JWT signé avec identifiant de commande, de magasin et expiration), affiché sous forme de code QR dans l’application mobile et le compte web.

**Critères d’acceptation :**
- **Critère du cahier :** le code QR ne peut être ni falsifié ni modifié.
- **Critères complémentaires proposés (à valider) :** Le QR est émis uniquement pour une commande prête, avec identifiants commande/magasin et expiration; toute modification invalide sa signature.

**Traçabilité :** `A-PCK-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-026 — A-PCK-02 · Must

**Récit utilisateur :** En tant que commis, je veux scanner un QR ou saisir les données de commande, afin de vérifier rapidement l’identité de la commande à remettre.

**Exigence source :** L’application de bureau lit le code QR (webcam ou lecteur USB agissant comme clavier) ou accepte la saisie manuelle du numéro de commande + nom de famille du client.

**Critères d’acceptation :**
- **Critère du cahier :** une commande d’un autre magasin ou déjà récupérée est refusée avec un message clair.
- **Critères complémentaires proposés (à valider) :** La lecture par caméra/lecteur ou la saisie manuelle fonctionne; les commandes d’un autre magasin ou déjà récupérées sont refusées.

**Traçabilité :** `A-PCK-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-027 — A-PCK-03 · Must

**Récit utilisateur :** En tant que commis, je veux confirmer la remise d’une commande, afin d’éviter une seconde remise.

**Exigence source :** La validation marque la commande `picked_up` et enregistre le commis et l’heure; le jeton devient inutilisable.

**Critères d’acceptation :**
- **Critère du cahier :** une deuxième lecture échoue.
- **Critères complémentaires proposés (à valider) :** La validation passe la commande à picked_up, mémorise le commis et l’heure et rend le jeton inutilisable.

**Traçabilité :** `A-PCK-03` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-028 — A-PCK-04 · Should

**Récit utilisateur :** En tant que gérant, je veux identifier les commandes non récupérées depuis sept jours, afin de décider de leur annulation et du remboursement.

**Exigence source :** Les commandes non récupérées après 7 jours sont signalées; le gérant peut annuler et rembourser, ce qui libère le stock.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les commandes concernées sont signalées; l’annulation autorisée libère le stock et lance le remboursement test.

**Traçabilité :** `A-PCK-04` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.5 Gestion des stocks


#### US-029 — A-INV-01 · Must

**Récit utilisateur :** En tant qu’employé de magasin, je veux consulter et tracer chaque mouvement de stock, afin de connaître les quantités fiables par magasin.

**Exigence source :** Niveau de stock par produit et par magasin; chaque changement est enregistré dans `stock_movements` (type : vente, réservation, libération, réception, ajustement, retour, transfert; quantité; auteur; motif; horodatage).

**Critères d’acceptation :**
- **Critère du cahier :** le stock courant égale la somme des mouvements (requête de vérification fournie).
- **Critères complémentaires proposés (à valider) :** Chaque mouvement a type, quantité, auteur, motif et date; la quantité courante est réconciliable avec les mouvements.

**Traçabilité :** `A-INV-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-030 — A-INV-02 · Must

**Récit utilisateur :** En tant que gérant, je veux enregistrer la réception de marchandises, afin de mettre à jour les stocks reçus.

**Exigence source :** Réception : le gérant saisit les quantités reçues pour une liste de produits (p. ex. bordereau de livraison).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Une réception de plusieurs produits crée les mouvements correspondants dans le bon magasin; les nouvelles quantités sont visibles.

**Traçabilité :** `A-INV-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-031 — A-INV-03 · Should

**Récit utilisateur :** En tant qu’employé de magasin, je veux déclarer un ajustement avec justification, afin de corriger les écarts de stock de manière contrôlée.

**Exigence source :** Ajustements (perte, bris, correction d’inventaire) avec motif obligatoire; les ajustements au-delà d’un seuil (p. ex. 20 unités ou 500 $) exigent l’approbation du gérant.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le motif est obligatoire; un ajustement dépassant le seuil défini exige l’approbation du gérant.

**Traçabilité :** `A-INV-03` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-032 — A-INV-04 · Should

**Récit utilisateur :** En tant que gérant, je veux consulter et exporter les articles en stock faible, afin de anticiper les réapprovisionnements.

**Exigence source :** Alerte de stock faible lorsque la quantité < seuil de réapprovisionnement; liste exportable en CSV.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les articles sous leur seuil apparaissent dans une liste; l’export CSV reprend les résultats.

**Traçabilité :** `A-INV-04` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-033 — A-INV-05 · Must

**Récit utilisateur :** En tant que commis, je veux préparer les commandes payées de mon magasin, afin de signaler leur disponibilité pour la cueillette.

**Exigence source :** Écran de préparation des commandes : liste des commandes payées du magasin du commis, cocher les articles préparés, marquer la commande comme prête.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Seules les commandes du magasin affecté apparaissent; les articles peuvent être cochés et la commande marquée prête.

**Traçabilité :** `A-INV-05` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-034 — A-INV-06 · Could

**Récit utilisateur :** En tant que commis, je veux enregistrer un retour admissible, afin de rembourser et remettre en stock les articles revendables.

**Exigence source :** Retours dans les 30 jours avec preuve d’achat : remise en stock (si revendable) et déclenchement du remboursement.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le retour exige une preuve d’achat et respecte le délai de 30 jours; le stock est ajusté seulement si l’article est revendable.

**Traçabilité :** `A-INV-06` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-035 — A-INV-07 · Could

**Récit utilisateur :** En tant que gérant, je veux demander et confirmer un transfert entre magasins, afin de rééquilibrer les stocks.

**Exigence source :** Demande et confirmation de transfert entre magasins.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le transfert désigne un magasin source et destination; sa confirmation enregistre les mouvements correspondants.

**Traçabilité :** `A-INV-07` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.6 Administration et rapports


#### US-036 — A-ADM-01 · Must

**Récit utilisateur :** En tant qu’administrateur, je veux créer, modifier et désactiver des produits, catégories et marques, afin de maintenir le catalogue à jour.

**Exigence source :** Gestion (CRUD) des produits (champs bilingues et téléversement d’images avec validation du type et de la taille), des catégories et des marques.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les champs bilingues sont modifiables; les images sont contrôlées par type et taille; les opérations sont réservées aux administrateurs.

**Traçabilité :** `A-ADM-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** L1 — Fondations


#### US-037 — A-ADM-02 · Must

**Récit utilisateur :** En tant qu’administrateur, je veux gérer les comptes, rôles et affectations du personnel, afin de contrôler les accès aux magasins.

**Exigence source :** Gestion des utilisateurs : création des comptes du personnel, attribution du rôle et du magasin, désactivation des comptes (aucune suppression définitive de l’historique du personnel).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Un compte du personnel peut être créé, affecté et désactivé; l’historique du personnel n’est pas effacé.

**Traçabilité :** `A-ADM-02` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-038 — A-ADM-03 · Should

**Récit utilisateur :** En tant qu’administrateur, je veux consulter les indicateurs commerciaux, afin de piloter les ventes et les stocks.

**Exigence source :** Tableau de bord : ventes par jour et par magasin, 10 meilleurs produits, panier moyen, articles en stock faible, commandes par statut (graphiques).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le tableau présente ventes par jour/magasin, top 10, panier moyen, stock faible et commandes par statut.

**Traçabilité :** `A-ADM-03` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-039 — A-ADM-04 · Should

**Récit utilisateur :** En tant qu’administrateur, je veux consulter les changements sensibles, afin de auditer les actions sur les prix, rôles et stocks.

**Exigence source :** Consultation du journal d’audit : qui a modifié des prix, des rôles, des ajustements de stock (filtrable).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le journal présente auteur, action, date et cible; les événements sont filtrables.

**Traçabilité :** `A-ADM-04` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-040 — A-ADM-05 · Should

**Récit utilisateur :** En tant qu’administrateur, je veux gérer les documents de l’assistant, afin de maintenir ses réponses fondées sur des sources approuvées.

**Exigence source :** Gestion de la base de connaissances de l’agent : téléverser/remplacer des documents, relancer l’ingestion, voir les statistiques de rétroaction.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les documents peuvent être ajoutés ou remplacés; une réingestion peut être lancée; les statistiques de rétroaction sont consultables.

**Traçabilité :** `A-ADM-05` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-041 — A-ADM-06 · Could

**Récit utilisateur :** En tant qu’administrateur, je veux importer des produits à partir d’un fichier CSV, afin de mettre à jour le catalogue en lot.

**Exigence source :** Importation de produits par CSV (avec rapport de validation).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Les lignes valides sont importées selon la stratégie retenue; un rapport signale les erreurs et les lignes rejetées.

**Traçabilité :** `A-ADM-06` · **MoSCoW :** Could · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.7 Compte client et vie privée


#### US-042 — A-PRV-01 · Must

**Récit utilisateur :** En tant que client, je veux modifier mon profil et mes préférences, afin de garder mes informations à jour.

**Exigence source :** Gestion du profil (nom, langue, préférences de communication).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le nom, la langue et les préférences de communication peuvent être enregistrés et relus.

**Traçabilité :** `A-PRV-01` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-043 — A-PRV-02 · Should

**Récit utilisateur :** En tant que client, je veux exporter mes renseignements personnels, afin de exercer mon droit d’accès et de portabilité.

**Exigence source :** Exportation des renseignements personnels (JSON) sur demande (droit d’accès et de portabilité, Loi 25).

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Une demande autorisée génère un fichier JSON des renseignements personnels associés au compte.

**Traçabilité :** `A-PRV-02` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-044 — A-PRV-03 · Should

**Récit utilisateur :** En tant que client, je veux demander la suppression de mon compte, afin de limiter la conservation de mes données personnelles.

**Exigence source :** Demande de suppression du compte : renseignements personnels anonymisés, commandes conservées pour la comptabilité avec une référence client anonymisée.

**Critères d’acceptation :**
- **Critère du cahier :** après suppression, connexion impossible et champs personnels anonymisés; dossiers financiers intacts.
- **Critères complémentaires proposés (à valider) :** Après traitement, la connexion échoue, les champs personnels sont anonymisés et les données financières requises sont conservées.

**Traçabilité :** `A-PRV-03` · **MoSCoW :** Should · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


#### US-045 — A-PRV-04 · Must

**Récit utilisateur :** En tant que visiteur, je veux choisir mes consentements aux témoins et aux communications, afin de contrôler l’utilisation de mes données.

**Exigence source :** Bandeau de témoins et de consentement sur l’application web; courriels promotionnels sur adhésion seulement.

**Critères d’acceptation :**
- **Critères complémentaires proposés (à valider) :** Le bandeau permet un choix explicite; les courriels promotionnels ne sont envoyés qu’après adhésion.

**Traçabilité :** `A-PRV-04` · **MoSCoW :** Must · **Issue GitHub :** [à identifier / relier] · **Estimation :** [à compléter] · **Jalon :** [à attribuer selon le plan L1/L2/L3]


### 8.8 Assistant conversationnel « Conseiller Laurentien » — récits complémentaires proposés

> **Source :** section A.9 du cahier des charges. Cette section décrit des comportements et règles mais n’attribue pas d’identifiants `A-RAG-*` ni de priorités MoSCoW individuelles. Les identifiants et priorités ci-dessous sont **proposés**, à valider par l’équipe; ils ne sont pas présentés comme des exigences officielles numérotées.


#### US-RAG-01 · Must proposé

**Récit utilisateur :** En tant que client, je veux poser une question en français ou en anglais, afin d’obtenir une réponse utile dans ma langue.

**Critères d’acceptation proposés (à valider) :** La réponse s’appuie sur des documents approuvés et cite ses sources; si le contexte est insuffisant, l’assistant l’indique et propose de contacter le magasin.

**Source :** A.9 / A.9.2 / A.9.3 · **Priorité :** Must proposé · **Issue GitHub :** [à identifier / relier] · **Jalon :** RAG à partir de L2 (voir A.11).


#### US-RAG-02 · Must proposé

**Récit utilisateur :** En tant que client, je veux consulter une information de prix ou de disponibilité fiable, afin d’éviter de me déplacer pour un article indisponible.

**Critères d’acceptation proposés (à valider) :** L’assistant n’invente jamais de prix ou de stock à partir des documents; il renvoie à la fiche produit ou consulte l’API en temps réel si cet outil est implémenté.

**Source :** A.9 / A.9.2 / A.9.3 · **Priorité :** Must proposé · **Issue GitHub :** [à identifier / relier] · **Jalon :** RAG à partir de L2 (voir A.11).


#### US-RAG-03 · Must proposé

**Récit utilisateur :** En tant que client, je veux recevoir des conseils prudents sur des travaux sensibles, afin de ne pas suivre des instructions dangereuses.

**Critères d’acceptation proposés (à valider) :** Pour l’électricité, le gaz ou la structure au-delà des conseils de base, l’assistant recommande un professionnel qualifié; les questions hors sujet sont refusées.

**Source :** A.9 / A.9.2 / A.9.3 · **Priorité :** Must proposé · **Issue GitHub :** [à identifier / relier] · **Jalon :** RAG à partir de L2 (voir A.11).


#### US-RAG-04 · Should proposé

**Récit utilisateur :** En tant qu’administrateur, je veux maintenir une base documentaire approuvée, afin d’assurer la fiabilité des réponses.

**Critères d’acceptation proposés (à valider) :** Les documents couvrent politiques, guides et fiches produits; les avis non assainis ne sont pas ingérés; l’évaluation inclut les questions de la section A.9.3.

**Source :** A.9 / A.9.2 / A.9.3 · **Priorité :** Should proposé · **Issue GitHub :** [à identifier / relier] · **Jalon :** RAG à partir de L2 (voir A.11).


## 9. Exigences non fonctionnelles communes


- **ENF-01** — Sécurité Les risques de l’OWASP Top 10 (2021) sont traités et documentés dans l’audit de sécurité (L3). Aucune vulnérabilité critique ou élevée détectée par ZAP ne reste sans explication.

- **ENF-02** — Sécurité Mots de passe hachés avec Argon2id (ou bcrypt coût ≥ 12). Aucun secret (clé d’API, mot de passe de BD, secret JWT) dans le dépôt; secrets conservés dans les variables d’environnement ou le gestionnaire de secrets de l’hébergeur.

- **ENF-03** — Sécurité Tout le trafic en HTTPS. CORS limité aux origines connues. En-têtes de sécurité configurés (HSTS, X-Content-Type-Options, Content-Security-Policy pour l’application web, Referrer-Policy).

- **ENF-04** — Sécurité Autorisation vérifiée côté serveur pour chaque point de terminaison (contrôle du rôle ET de la propriété). Des tests automatisés prouvent que l’utilisateur X ne peut pas accéder aux ressources de l’utilisateur Y.

- **ENF-05** — Sécurité Limitation de débit sur la connexion, l’inscription, la réinitialisation du mot de passe et l’agent conversationnel (p. ex. slowapi). Verrouillage de compte ou délai progressif après des échecs répétés.

- **ENF-06** — Vie privée Conformité à la Loi 25 (Loi sur la protection des renseignements personnels dans le secteur privé, telle que modifiée) : consentement explicite, politique de confidentialité, droits d’accès et de suppression, collecte minimale, personne responsable de la protection des renseignements personnels (fictive).

- **ENF-07** — Performance Temps de réponse médian de l’API < 300 ms pour les lectures en charge normale; première réponse de l’agent conversationnel < 8 s. Listes paginées (aucun point de terminaison ne renvoie une collection non bornée).

- **ENF-08** — Fiabilité Les transactions sont atomiques : une défaillance en cours de commande ou de réservation ne laisse aucune donnée partielle. Procédure de sauvegarde et de restauration documentée et testée au moins une fois.

- **ENF-09** — Utilisabilité et L’application web respecte l’essentiel des WCAG 2.1 niveau AA : navigation accessibilité au clavier, étiquettes, contraste, textes de remplacement. Application mobile utilisable d’une seule main pour les parcours principaux.

- **ENF-10** — Bilinguisme Interfaces disponibles en français et en anglais (fichiers i18n, aucune chaîne codée en dur). Le français est la langue par défaut, conformément à la Charte de la langue française.

- **ENF-11** — Maintenabilité Analyse statique et formatage imposés en CI (ruff/black pour Python, ESLint/Prettier pour JS, dotnet format pour C#). Architecture en couches; aucune logique d’affaires dans les routeurs ou les vues.

- **ENF-12** — Testabilité Couverture de tests de l’API ≥ 60 % au L2 et ≥ 70 % au L3. Les règles d’affaires critiques (stocks, réservations, paiements, autorisations) ont des tests dédiés.

- **ENF-13** — Observabilité Journaux structurés (JSON) avec identifiant de requête; erreurs journalisées sans renseignements personnels ni secrets; point de terminaison de santé `/health`.

- **ENF-14** — Portabilité L’application s’exécute localement selon une procédure unique documentée (README); Docker Compose facultatif mais recommandé.

## 10. Règles d’affaires


- **RA-A-01** — Les stocks sont gérés par magasin. Une commande est rattachée à un seul magasin de cueillette; tous ses articles doivent y être disponibles.

- **RA-A-02** — Quantité disponible = quantité en main − quantité réservée. Les réservations expirent après 15 minutes sans paiement.

- **RA-A-03** — Taxes : TPS 5 % et TVQ 9,975 % calculées sur le sous-total après rabais et arrondies au cent (règle d’arrondi documentée).

- **RA-A-04** — Les prix sont stockés en cents (entier) ou en NUMERIC(10,2), jamais en nombre à virgule flottante.

- **RA-A-05** — Le client peut annuler une commande seulement à l’état `paid` (avant la préparation). Ensuite, seul un gérant peut annuler.

- **RA-A-06** — Un jeton de cueillette est valide seulement pour son magasin, une seule fois, et uniquement tant que la commande est `ready_for_pickup`.

- **RA-A-07** — Quantité maximale par produit et par commande : 20 (pour limiter l’accaparement et les abus).

- **RA-A-08** — Retours acceptés dans les 30 jours sur présentation du numéro de commande; remboursement sur le mode de paiement d’origine.

- **RA-A-09** — Les changements de prix ne sont jamais rétroactifs : une commande conserve le prix unitaire et les taux de taxe en vigueur au moment de l’achat.

## 11. Exigences transversales des applications

- Architecture : une API REST versionnée /api/v1, FastAPI (Python), PostgreSQL 16 + pgvector; clients React/Vite, mobile React Native/Expo ou .NET MAUI, bureau C# .NET 8 WPF ou MAUI.
- Web : accueil, catégories, recherche, fiche, magasin, panier, paiement, commandes, administration et widget de clavardage bilingue.
- Mobile : catalogue, panier, suivi, QR affichable hors ligne une fois chargé, stockage sécurisé des jetons.
- Bureau : connexion et MFA, préparation, validation QR ou saisie manuelle, réception et ajustements, gestion d’erreurs API.
- Agent RAG : base de connaissances approuvée (au moins 25 documents FR/EN et 15 000 mots), citations, refus hors portée, aucune donnée personnelle dans la base, évaluation de 20 questions à L2 puis 40 à L3.

## 12. Traçabilité, validation et plan de livraison


Chaque récit est relié à une issue GitHub; chaque issue doit indiquer l’ID source, les critères d’acceptation, la priorité, les tests et la demande de fusion. Une exigence ne sera considérée terminée qu’après validation et tests pertinents. Les décisions de modification de portée doivent faire l’objet d’une issue change-request approuvée.

**Échéancier de travail à confirmer :** les sections détaillées de la Partie IV et A.11 indiquent L1 semaine 3, L2 semaine 6 et L3 semaine 8, tandis que la couverture du cahier indique L1 semaine 2, L2 semaine 4 et L3 semaine 5. Cette contradiction reste ouverte et doit être arbitrée par le responsable; aucune échéance définitive n’est présumée.


### 12.1 Matrice de périmètre et de validation L1

La priorité **Must** désigne une obligation du produit complet; elle ne signifie pas que la fonctionnalité doit être développée en L1. Le périmètre fonctionnel explicite de L1, selon A.11, est le suivant :

| Élément L1 | Exigences ou volume | Preuve de réception attendue | État documentaire |
|---|---|---|---|
| Authentification | A-AUTH-01 à 05 et A-AUTH-07 | Scénarios automatisés, routes et démonstration de connexion, vérification et contrôles d’accès | Implémentation rapportée; réception L1 à confirmer |
| Catalogue | A-CAT-01 à 03 | Pagination ≤ 50, catégories, fiche bilingue, disponibilité calculée et recherche FR/EN sans accents | Preuves à produire |
| Administration | A-ADM-01 | CRUD produits/catégories/marques, contrôle des images et autorisations | Preuves à produire |
| Amorçage | 3 magasins, ≥ 150 produits et leurs stocks | Script rejouable, inventaire et requêtes de contrôle | Preuves à produire |
| Client Web | Catalogue et fiche produit | URL déployée et scénario de consultation | Preuves à produire |
| Client Mobile | Connexion à l’API en ligne et liste de produits | Démonstration sur simulateur ou appareil | Preuves à produire |
| Client Bureau | Connexion à l’API en ligne et liste de produits | Démonstration Windows | Preuves à produire |
| Incrément déployé | API et clients intégrés | URL(s), procédure et démonstration de bout en bout | Preuves à produire |

**État documentaire ≠ conformité du logiciel.** La présence d’un récit dans ce document ne prouve pas que le code, le déploiement ou le test existent. Les éléments « preuves à produire » ne doivent être cochés qu’après vérification.

### 12.2 Traçabilité opérationnelle et critères de réception

Pour chaque exigence, consigner : **ID source → récit → jalon → issue → PR/commit → test → résultat/artefact → validateur/date**. Une issue existante ne vaut pas à elle seule preuve de conformité. Les estimations et responsables restent à attribuer par l’équipe.

**Critères complémentaires proposés pour L1 (à approuver, non substitués aux critères officiels) :**

| ID | Scénario complémentaire mesurable |
|---|---|
| A-AUTH-01 | Créer un compte, vérifier l’horodatage du consentement et refuser une commande avant vérification du courriel. |
| A-AUTH-02 | Un jeton expiré retourne HTTP 401; un rafraîchissement valide fonctionne; un rafraîchissement révoqué échoue. |
| A-AUTH-03 | Rejeter un mot de passe de moins de 12 caractères ou courant; vérifier l’absence de mot de passe en clair en base et dans les journaux. |
| A-AUTH-04 | Un jeton de réinitialisation expire après 30 minutes, n’est utilisable qu’une fois et ne permet pas l’énumération de comptes. |
| A-AUTH-05 | Tester l’accès autorisé et refusé par rôle, y compris l’isolation des magasins pour le personnel. |
| A-AUTH-07 | Démontrer par script la limitation de débit et le verrouillage progressif selon la configuration retenue. |
| A-CAT-01 | Vérifier la limite de 50 résultats par page, la navigation hiérarchique et les tris prix/nom/nouveauté. |
| A-CAT-02 | Vérifier champs FR/EN, SKU, prix, images, caractéristiques JSONB et disponibilité dérivée du stock de chaque magasin. |
| A-CAT-03 | Vérifier que « perceuse », « drill » et « equerre » retrouvent les résultats attendus avec recherche FR/EN et `unaccent`. |
| A-ADM-01 | Vérifier création/lecture/modification/suppression selon la politique retenue, catégories/marques, validation du type/taille des images et refus d’accès aux non-administrateurs. |

**Réception documentaire :** le responsable du projet approuve la portée, les critères ajoutés, les échéances et la traçabilité. **Réception fonctionnelle :** les démonstrations et preuves techniques sont disponibles.

### 12.3 Méthode de mesure des objectifs

Les indicateurs de la section 4 sont des cibles du produit. Pour les rendre auditables, conserver pour chaque essai : date, version, environnement, jeu de données, scénario, durée ou résultat mesuré, journal de test et décision d’acceptation. Les objectifs de paiement, de concurrence sur les stocks, de cueillette QR et de qualité RAG concernent les jalons où ces capacités sont prévues; ils ne doivent pas être présentés comme acquis en L1.

## 13. Risques et points de vigilance

- Survente en concurrence : test de 50 acheteurs sur 5 unités et stratégie de verrouillage documentée.
- Falsification des prix : calcul exclusif côté serveur et tests.
- Webhooks dupliqués ou falsifiés : signature vérifiée et idempotence.
- Accès non autorisé aux commandes ou magasins : contrôles de rôle et de propriété côté serveur.
- Injection d’invite dans le RAG : documents contrôlés, assainissement et tests adverses.
- Erreurs monétaires : entiers en cents ou Decimal, règles d’arrondi documentées.

## 14. Points à compléter / validation

- ☐ Nom de l’équipe, membres, date de validation et approbateur.
- ☐ Identifier les numéros et liens réels des issues GitHub par exigence, les responsables, les estimations et les preuves de tests.
- ☐ Arbitrer la contradiction des semaines de livraison (couverture vs sections détaillées) et confirmer les dates calendaires.
- ☐ Approuver les critères de test complémentaires proposés et compléter ceux des exigences sans CA explicite.
- ☐ Confirmation des choix techniques recommandés et des décisions d’architecture dans le document séparé.

## 15. Référence documentaire


Source unique : « RCW : Projet Final — Cahier des charges », version 1.0, octobre 2026. Parties I (architecture et ENF), II (A.1 à A.11), IV (livrables) et annexe A (gabarit de récit utilisateur).
