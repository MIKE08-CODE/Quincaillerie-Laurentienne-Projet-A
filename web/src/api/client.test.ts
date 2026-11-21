import { describe, expect, it, vi } from "vitest";

import { ApiError, buildUrl, getJson } from "./client";

describe("buildUrl", () => {
  it("ajoute le préfixe /api/v1 et ignore les paramètres vides", () => {
    expect(buildUrl("/products", { page: 2, size: 24, category_id: undefined, q: "" })).toBe(
      "/api/v1/products?page=2&size=24",
    );
  });

  it("encode les caractères spéciaux", () => {
    expect(buildUrl("/search", { q: "équerre & co" })).toBe("/api/v1/search?q=%C3%A9querre+%26+co");
  });
});

describe("getJson", () => {
  it("transforme une erreur de l'API en ApiError avec son code stable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: { code: "product_not_found", message: "x" } }), { status: 404 })),
    );
    await expect(getJson("/products/x")).rejects.toMatchObject({ status: 404, code: "product_not_found" });
  });

  it("signale une API injoignable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const error = await getJson("/stores").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("network_error");
  });

  it("gère une réponse d'erreur sans corps JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("oups", { status: 502, statusText: "Bad Gateway" })));
    await expect(getJson("/stores")).rejects.toMatchObject({ status: 502, code: "http_502" });
  });
});
