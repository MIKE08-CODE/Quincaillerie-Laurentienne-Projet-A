# Registre des risques — L1

Mis à jour le 21 novembre 2026. Échelle : probabilité et impact de 1 (faible) à 3 (élevé) ; criticité =
probabilité × impact. **Responsables : à compléter** par l'équipe.

| ID | Risque | P | I | C | Mesure | État | Responsable |
|---|---|---|---|---|---|---|---|
| R1 | **L1 non déployée à l'échéance** : aucune URL en ligne alors que §9.1 l'exige | 3 | 3 | 9 | Procédure prête (PR #33) ; décisions d'hébergement et de secrets à prendre au plus tôt | Ouvert | À compléter |
| R2 | **Courriels non envoyés en production** : inscription et réinitialisation en échec | 3 | 3 | 9 | Choisir un fournisseur (offre gratuite) ou un mode de démonstration documenté | Ouvert — décision requise | À compléter |
| R3 | Accumulation de PR non fusionnées, mises à jour en cascade (ruleset `strict`) | 2 | 2 | 4 | Ordre de fusion défini (checklist) ; PR courtes | Ouvert | MIKE08-CODE |
| R4 | Un seul développeur autorisé à fusionner, sans relecture (0 approbation) | 2 | 3 | 6 | CI obligatoire ; écart avec §6.1 consigné | Accepté (décision du responsable) | MIKE08-CODE |
| R5 | Écart entre le contrat d'API et le code (format d'erreur) | 2 | 2 | 4 | ADR-008, sous-lot 0.A planifié ; écart consigné au §18 du contrat | Ouvert | À compléter |
| R6 | Dépendances : PR Dependabot #24 bloquée (Ruff UP042), #25 en attente ; vulnérabilités modérées de l'outillage Expo | 2 | 2 | 4 | Issue #26 ; exception documentée (mobile) | Ouvert | À compléter |
| R7 | Extension `unaccent` indisponible chez l'hébergeur de la base | 1 | 3 | 3 | Vérification avant la première migration (procédure §1) | Ouvert | À compléter |
| R8 | Limitation de débit faussée derrière deux relais (Vercel puis Render) | 2 | 2 | 4 | Vérifier `X-Forwarded-For` après déploiement | Ouvert | À compléter |
| R9 | Mise en veille des services gratuits pendant la démonstration | 2 | 2 | 4 | Réveiller l'API avant la démonstration ; plan de repli en local | Ouvert | À compléter |
| R10 | Client mobile jamais exécuté sur un appareil | 2 | 2 | 4 | Démonstration Expo Go ou émulateur à répéter avant la remise | Ouvert | À compléter |
| R11 | Deux versions majeures de React (web 18, mobile 19) | 1 | 1 | 1 | ADR-007 ; aucun code partagé | Accepté sous réserve d'approbation | À compléter |
| R12 | Contradiction d'échéancier du cahier (L1 en semaine 2 ou 3) | 2 | 3 | 6 | À arbitrer par le responsable (point ouvert O16) | Ouvert | Responsable du projet |
| R13 | Charge de travail : trois clients, l'API et le déploiement pour une petite équipe | 3 | 2 | 6 | Périmètre minimal L1 pour le mobile et le bureau ; priorisation par issues | Ouvert | À compléter |
