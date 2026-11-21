import { useReducer } from "react";

/** Compteur à inclure dans les dépendances de useApi pour relancer une requête (« Réessayer »). */
export function useReload(): [number, () => void] {
  return useReducer((n: number) => n + 1, 0);
}
