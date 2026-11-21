# ADR-008 — Format uniforme des erreurs `ErrorOut` et `X-Request-ID`

- **Statut :** Accepté dans son principe (orientations D1, O1 à O4, 21 novembre 2026) — **non implémenté** (sous-lot 0.A).
- **Exigences :** contrat d'API §6, ENF-13 (identifiant de requête dans les journaux), A-AUTH-04 (non-énumération).

## Contexte

L'API renvoie aujourd'hui `{"detail": {"code", "message"}}` (et `errors[].reason` pour les 422). Le
contrat cible prévoit `ErrorOut {code, message, details, request_id}` et
`ValidationErrorOut {code: "validation_error", message, errors[{field, message, type}], request_id}`.

## Décision

- `code` générique du contrat ; code métier précis conservé dans `details.reason`.
- `X-Request-ID` généré par le serveur (jamais repris du client), présent sur toutes les réponses et
  dans les journaux.
- Toutes les erreurs 422, y compris celles de la politique de mot de passe, au format `ValidationErrorOut`.
- Verrouillage du compte en **429** avec `Retry-After`, sous réserve de tests de non-énumération (O4).
- Mise en œuvre en trois commits : tests de référence, implémentation, nouveaux tests et documentation.

## Conséquences

- Les clients web, mobile et bureau lisent aujourd'hui `detail.code` : ils devront lire `code` et
  `details.reason` après la migration (adaptation prévue dans le même lot).
- Tant que ce lot n'est pas fusionné, le contrat et l'API divergent sur le format des erreurs : l'écart
  est consigné dans le contrat (§18).
