import { buildUrl } from "../api/client";
import { normalizeApiUrl } from "../config";

describe("configuration de l'URL de l'API", () => {
  it("utilise l'adresse locale par défaut et retire la barre oblique finale", () => {
    expect(normalizeApiUrl(undefined)).toBe("http://localhost:8000/api/v1");
    expect(normalizeApiUrl("  ")).toBe("http://localhost:8000/api/v1");
    expect(normalizeApiUrl("https://api.example.com/api/v1/")).toBe("https://api.example.com/api/v1");
  });

  it("construit les URL avec des paramètres encodés et sans valeurs vides", () => {
    expect(buildUrl("/products", { page: 2, size: 20, category_id: undefined }, "https://h/api/v1")).toBe(
      "https://h/api/v1/products?page=2&size=20",
    );
    expect(buildUrl("/search", { q: "équerre & co" }, "https://h/api/v1")).toBe(
      "https://h/api/v1/search?q=%C3%A9querre%20%26%20co",
    );
  });
});
