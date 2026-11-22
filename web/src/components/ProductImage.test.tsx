import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PLACEHOLDER_IMAGE, ProductImage } from "./ProductImage";

describe("ProductImage", () => {
  it("affiche l'image du produit quand elle existe", () => {
    render(<ProductImage src="https://cdn.example.com/a.jpg" alt="Perceuse" width={240} height={180} />);
    const img = screen.getByRole("img", { name: "Perceuse" });
    expect(img).toHaveAttribute("src", "https://cdn.example.com/a.jpg");
    expect(img).not.toHaveAttribute("data-placeholder");
  });

  it("remplace une image qui ne se charge pas par l'image locale", () => {
    const { container } = render(
      <ProductImage src="https://images.inexistant.example/a.jpg" alt="Perceuse" width={240} height={180} />,
    );
    const img = container.querySelector("img")!;
    fireEvent.error(img);
    expect(img).toHaveAttribute("src", PLACEHOLDER_IMAGE);
    expect(img).toHaveAttribute("data-placeholder", "true");
    expect(img).toHaveAttribute("alt", ""); // image décorative : pas de texte trompeur
  });

  it("utilise l'image locale quand le produit n'a pas d'image", () => {
    const { container } = render(<ProductImage src={null} alt="Perceuse" width={240} height={180} />);
    expect(container.querySelector("img")).toHaveAttribute("src", PLACEHOLDER_IMAGE);
  });

  it("utilise une image servie par le site (compatible avec la CSP img-src 'self')", () => {
    expect(PLACEHOLDER_IMAGE.startsWith("/")).toBe(true);
  });
});
