import { useEffect, useState } from "react";

import { ApiError } from "../api/client";

export type ApiState<T> =
  | { status: "loading" }
  | { status: "error"; error: ApiError }
  | { status: "success"; data: T };

/**
 * Lance une requête à chaque changement de `deps` et annule la précédente (AbortController) :
 * une réponse tardive ne remplace jamais une réponse plus récente.
 */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, deps: readonly unknown[]): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    load(controller.signal).then(
      (data) => setState({ status: "success", data }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          error: error instanceof ApiError ? error : new ApiError(0, "unknown_error", String(error)),
        });
      },
    );
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- les dépendances sont fournies par l'appelant
  }, deps);

  return state;
}
