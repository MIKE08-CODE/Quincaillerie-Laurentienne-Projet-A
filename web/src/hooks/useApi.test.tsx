import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "../api/client";
import { useApi } from "./useApi";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useApi", () => {
  it("passe de « chargement » au résultat, puis revient en chargement quand les dépendances changent", async () => {
    const pending = new Map<string, ReturnType<typeof deferred<string>>>();
    const { result, rerender } = renderHook(({ id }) => useApi(() => {
      const d = deferred<string>();
      pending.set(id, d);
      return d.promise;
    }, [id]), { initialProps: { id: "a" } });

    expect(result.current).toEqual({ status: "loading" });
    await act(async () => pending.get("a")!.resolve("A"));
    expect(result.current).toEqual({ status: "success", data: "A" });

    rerender({ id: "b" });
    expect(result.current).toEqual({ status: "loading" }); // pas de donnée périmée affichée
    await act(async () => pending.get("b")!.resolve("B"));
    expect(result.current).toEqual({ status: "success", data: "B" });
  });

  it("ignore une réponse tardive d'une requête annulée", async () => {
    const pending = new Map<string, ReturnType<typeof deferred<string>>>();
    const { result, rerender } = renderHook(({ id }) => useApi(() => {
      const d = deferred<string>();
      pending.set(id, d);
      return d.promise;
    }, [id]), { initialProps: { id: "a" } });

    rerender({ id: "b" });
    await act(async () => pending.get("b")!.resolve("B"));
    await act(async () => pending.get("a")!.resolve("A tardif"));
    expect(result.current).toEqual({ status: "success", data: "B" });
  });

  it("expose une ApiError, y compris pour une erreur inattendue", async () => {
    const { result } = renderHook(() => useApi(() => Promise.reject(new Error("réseau")), []));
    await waitFor(() => expect(result.current.status).toBe("error"));
    const state = result.current as { status: "error"; error: ApiError };
    expect(state.error).toBeInstanceOf(ApiError);
    expect(state.error.code).toBe("unknown_error");
  });
});
