import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockApi, page, product, renderAt } from "../test/utils";

describe("Recherche (A-CAT-03)", () => {
  it("lance la recherche depuis l'en-tête et affiche les résultats", async () => {
    const fetchMock = mockApi((url) => {
      if (url.pathname === "/api/v1/search") return { body: page([product()], 1) };
      return { body: [] };
    });
    renderAt("/magasins");
    await userEvent.type(screen.getByLabelText("Rechercher un produit"), "  équerre ");
    await userEvent.click(screen.getByRole("button", { name: "Rechercher" }));
    expect(await screen.findByRole("heading", { name: "Résultats pour « équerre »" })).toBeInTheDocument();
    expect(await screen.findByText("Perceuse-visseuse sans fil 18 V")).toBeInTheDocument();
    const call = fetchMock.mock.calls
      .map(([u]) => new URL(String(u), "http://x"))
      .find((u) => u.pathname.endsWith("/search"));
    expect(call?.searchParams.get("q")).toBe("équerre");
  });

  it("indique qu'aucun produit ne correspond", async () => {
    mockApi(() => ({ body: page([], 0) }));
    renderAt("/recherche?q=zzzz");
    expect(await screen.findByText("Aucun produit ne correspond à « zzzz ».")).toBeInTheDocument();
  });

  it("invite à saisir un mot quand la requête est vide, sans appeler l'API", () => {
    const fetchMock = mockApi(() => ({ body: [] }));
    renderAt("/recherche?q=%20%20");
    expect(screen.getByText(/Saisissez un mot/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/search"))).toBe(false);
  });
});
