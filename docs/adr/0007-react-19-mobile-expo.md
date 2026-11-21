# ADR-007 — React 19 sur le mobile imposé par Expo SDK 58 ; React 18 conservé sur le web

- **Statut :** Proposé (à approuver) — constat fait lors de la PR #31, non fusionnée.
- **Lien :** complète l'ADR-003 (React Native + Expo) sans le modifier.

## Contexte

Le cahier impose React 18 pour l'application web. L'ADR-003 retient React Native + Expo pour le mobile.
Le gabarit officiel actuel d'Expo (SDK 58, React Native 0.88) fixe **React 19.3** : il n'existe pas de
combinaison Expo maintenue avec React 18.

## Options

1. Accepter React 19 sur le mobile seulement (web en React 18).
2. Revenir à un SDK Expo ancien compatible avec React 18 (versions non maintenues, vulnérabilités connues).
3. Changer de cadre mobile (contraire à l'ADR-003).

## Décision proposée

Option 1. Le web et le mobile ne partagent aucun code React ; seul le contrat de l'API est commun.

## Conséquences

- Deux versions majeures de React dans le dépôt, dans deux applications indépendantes.
- `@testing-library/react-native` 14 : `render` et `fireEvent` sont asynchrones (adapté dans les tests).
- Dependabot n'impose pas de montée majeure d'Expo ou de React Native : un changement de SDK se fait
  par une décision de l'équipe et `npx expo install --fix`.
- `npm audit` signale 3 vulnérabilités modérées dans l'outillage CLI d'Expo/Jest (non embarqué) ;
  exception documentée dans `mobile/README.md`.
