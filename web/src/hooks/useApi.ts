import { useEffect, useState } from "react";

import { ApiError } from "../api/client";

export type ApiState<T> =
  | { status: "loading" }
  | { status: "error"; error: ApiError }
  | { status: "success"; data: T };

type Settled<T> = { deps: readonly unknown[]; state: ApiState<T> };

function sameDeps(a: readonly unknown[], b: readonly unknown[]): boolean {
  return a.length === b.length && a.every((value, i) => Object.is(value, b[i]));
}

/**
 * Lance une requête à chaque changement de `deps` et annule la précédente (AbortController) :
 * une réponse tardive ne remplace jamais une réponse plus récente.
 * L'état « chargement » est déduit au rendu (aucun résultat, ou un résultat obtenu pour d'autres
 * `deps`) : aucun setState synchrone dans l'effet (règle react-hooks/set-state-in-effect).
 */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, deps: readonly unknown[]): ApiState<T> {
  const [settled, setSettled] = useState<Settled<T> | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setSettled({ deps, state: { status: "success", data } });
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setSettled({
          deps,
          state: {
            status: "error",
            error: error instanceof ApiError ? error : new ApiError(0, "unknown_error", String(error)),
          },
        });
      },
    );
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- les dépendances sont fournies par l'appelant
  }, deps);

  return settled && sameDeps(settled.deps, deps) ? settled.state : { status: "loading" };
}
