import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockApi, product, renderAt } from "../test/utils";

const detail = {
  ...product(),
  description_fr: "Perceuse compacte avec mandrin de 13 mm.",
  description_en: "Compact drill with a 13 mm chuck.",
  specs: { tension_v: 18, sans_fil: true, couleurs: ["jaune", "noir"] },
  images: [{ id: "i1", url: "https://images.example/perc.jpg", alt_fr: "Vue avant", alt_en: "Front view", position: 0 }],
  availability: [
    { store_id: "s1", store_name: "Saint-Jérôme", status: "in_stock" },
    { store_id: "s2", store_name: "Sainte-Agathe-des-Monts", status: "low_stock" },
    { store_id: "s3", store_name: "Mont-Tremblant", status: "out_of_stock" },
  ],
};

describe("Fiche produit (A-CAT-02)", () => {
  it("affiche la fiche bilingue, les caractéristiques et la disponibilité par magasin", async () => {
    mockApi((url) => (url.pathname.endsWith(`/products/${detail.id}`) ? { body: detail } : undefined));
    renderAt(`/produits/${detail.id}`);
    expect(await screen.findByRole("heading", { level: 1, name: detail.name_fr })).toBeInTheDocument();
    expect(screen.getByText(detail.description_fr)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Vue avant" })).toBeInTheDocument();
    expect(screen.getByText("En stock")).toBeInTheDocument();
    expect(screen.getByText("Stock faible")).toBeInTheDocument();
    expect(screen.getByText("Rupture")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Sans fil Oui/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Couleurs jaune, noir/ })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Changer la langue" }));
    expect(await screen.findByRole("heading", { level: 1, name: detail.name_en })).toBeInTheDocument();
    expect(screen.getByText("Low stock")).toBeInTheDocument();
    expect(screen.getByText(detail.description_en)).toBeInTheDocument();
    expect(screen.getByText(/\$129\.99/)).toBeInTheDocument();
  });

  it("indique qu'un produit inconnu est introuvable", async () => {
    mockApi(() => undefined);
    renderAt("/produits/inconnu");
    expect(await screen.findByText(/introuvable ou n.est plus offert/)).toBeInTheDocument();
  });

  it("affiche l'image téléversée (position 0) plutôt que l'ancienne image de remplacement (issue #10)", async () => {
    const withUpload = {
      ...detail,
      images: [
        { id: "i2", url: "https://res.cloudinary.com/demo-cloud/image/upload/v1/quincaillerie-laurentienne/products/p1/abc.jpg", alt_fr: "Perceuse", alt_en: "Drill", position: 0 },
        { id: "i1", url: "https://images.quincaillerie-laurentienne.example/products/perc.jpg", alt_fr: "Ancienne", alt_en: "Old", position: 1 },
      ],
    };
    mockApi((url) => (url.pathname.endsWith(`/products/${detail.id}`) ? { body: withUpload } : undefined));
    renderAt(`/produits/${detail.id}`);
    expect(await screen.findByRole("img", { name: "Perceuse" })).toHaveAttribute("src", "https://res.cloudinary.com/demo-cloud/image/upload/v1/quincaillerie-laurentienne/products/p1/abc.jpg");
  });
});
