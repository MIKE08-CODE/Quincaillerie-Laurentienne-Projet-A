import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { categories, mockApi, page, product, renderAt } from "../test/utils";

describe("Gabarit, accueil et magasins", () => {
  it("affiche l'accueil, les catégories et les nouveautés, puis bascule en anglais", async () => {
    mockApi((url) => {
      if (url.pathname.endsWith("/categories")) return { body: categories };
      if (url.pathname.endsWith("/products")) return { body: page([product()]) };
      return undefined;
    });
    renderAt("/");
    expect(await screen.findByRole("link", { name: "Outils" })).toHaveAttribute("href", "/produits?categorie=c0");
    expect(await screen.findByText("Perceuse-visseuse sans fil 18 V")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Changer la langue" }));
    expect(await screen.findByRole("link", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByText("Cordless drill driver 18 V")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });

  it("affiche une page introuvable pour une adresse inconnue", () => {
    mockApi(() => undefined);
    renderAt("/nimporte-quoi");
    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });

  it("affiche les magasins et leurs heures", async () => {
    mockApi(() => ({
      body: [
        {
          id: "s1",
          name: "Quincaillerie Laurentienne — Saint-Jérôme",
          address: "1200, boulevard du Curé-Labelle",
          phone: "450-555-0101",
          opening_hours: { mon: ["08:00", "21:00"] },
        },
      ],
    }));
    renderAt("/magasins");
    expect(await screen.findByRole("heading", { name: /Saint-Jérôme/ })).toBeInTheDocument();
    expect(screen.getByText("Lundi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "450-555-0101" })).toHaveAttribute("href", "tel:450-555-0101");
  });

  it("n'envoie pas de recherche vide", async () => {
    const fetchMock = mockApi(() => ({ body: [] }));
    renderAt("/magasins");
    await userEvent.type(screen.getByLabelText("Rechercher un produit"), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Rechercher" }));
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/search"))).toBe(false);
  });
});
