import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { categories, mockApi, page, product, renderAt } from "../test/utils";

function lastCall(fetchMock: ReturnType<typeof mockApi>, suffix: string): URL | undefined {
  return fetchMock.mock.calls
    .map(([u]) => new URL(String(u), "http://x"))
    .filter((u) => u.pathname.endsWith(suffix))
    .at(-1);
}

describe("Catalogue (A-CAT-01)", () => {
  it("affiche le chargement, puis les produits paginés et les catégories", async () => {
    const fetchMock = mockApi((url) => {
      if (url.pathname === "/api/v1/categories") return { body: categories };
      if (url.pathname === "/api/v1/products") return { body: page([product()], 157) };
      return undefined;
    });
    renderAt("/produits");
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Chargement");
    expect(await screen.findByText("Perceuse-visseuse sans fil 18 V")).toBeInTheDocument();
    expect(screen.getByText("157 produits")).toBeInTheDocument();
    expect(screen.getByText(/129,99/)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Pagination" })).toHaveTextContent("Page 1 sur 7");
    const call = lastCall(fetchMock, "/products");
    expect(call?.searchParams.get("size")).toBe("24");
    expect(call?.searchParams.get("sort")).toBe("newest");
  });

  it("filtre par catégorie, trie par prix et change de page", async () => {
    const fetchMock = mockApi((url) => {
      if (url.pathname === "/api/v1/categories") return { body: categories };
      if (url.pathname === "/api/v1/products") return { body: page([product()], 60) };
      return undefined;
    });
    renderAt("/produits");
    const nav = await screen.findByRole("navigation", { name: "Catégories" });
    await userEvent.click(within(nav).getByRole("button", { name: "Perceuses" }));
    await userEvent.selectOptions(screen.getByLabelText("Trier par"), "price_asc");
    await waitFor(() => {
      const last = lastCall(fetchMock, "/products");
      expect(last?.searchParams.get("category_id")).toBe("c1");
      expect(last?.searchParams.get("sort")).toBe("price_asc");
      expect(last?.searchParams.get("page")).toBe("1");
    });
    await userEvent.click(await screen.findByRole("button", { name: "Suivant" }));
    await waitFor(() => expect(lastCall(fetchMock, "/products")?.searchParams.get("page")).toBe("2"));
  });

  it("indique l'absence de produits", async () => {
    mockApi((url) => (url.pathname.endsWith("/categories") ? { body: categories } : { body: page([], 0) }));
    renderAt("/produits?categorie=c1");
    expect(await screen.findByText("Aucun produit dans cette catégorie.")).toBeInTheDocument();
  });

  it("affiche une erreur et permet de réessayer", async () => {
    let fail = true;
    mockApi((url) => {
      if (url.pathname.endsWith("/categories")) return { body: categories };
      if (fail) return { status: 500, body: { detail: { code: "internal_error", message: "x" } } };
      return { body: page([product()]) };
    });
    renderAt("/produits");
    expect(await screen.findByRole("alert")).toHaveTextContent("momentanément indisponible");
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Perceuse-visseuse sans fil 18 V")).toBeInTheDocument();
  });

  it("explique qu'une limite de requêtes est atteinte", async () => {
    mockApi((url) =>
      url.pathname.endsWith("/categories")
        ? { body: categories }
        : { status: 429, body: { detail: { code: "rate_limited", message: "x" } } },
    );
    renderAt("/produits");
    expect(await screen.findByRole("alert")).toHaveTextContent("Trop de requêtes");
  });
});
