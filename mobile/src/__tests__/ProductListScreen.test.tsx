import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import { ProductListScreen } from "../screens/ProductListScreen";

const categories = [
  { id: "c0", slug: "outils", name_fr: "Outils", name_en: "Tools", children: [] },
  { id: "c1", slug: "plomberie", name_fr: "Plomberie", name_en: "Plumbing", children: [] },
];

const product = (sku: string, overrides: Record<string, unknown> = {}) => ({
  id: `id-${sku}`,
  sku,
  name_fr: `Produit ${sku}`,
  name_en: `Product ${sku}`,
  brand: "Castor",
  price_cents: 1999,
  main_image_url: null,
  category_id: "c0",
  ...overrides,
});

type Reply = { status?: number; body: unknown };

function mockFetch(handler: (url: string) => Reply) {
  const fn = jest.fn(async (input: unknown) => {
    const { status = 200, body } = handler(String(input));
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    } as Response;
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

describe("ProductListScreen", () => {
  it("affiche un indicateur de chargement tant que l'API n'a pas répondu", async () => {
    globalThis.fetch = jest.fn(() => new Promise<Response>(() => undefined)) as unknown as typeof fetch;
    await render(<ProductListScreen lang="fr" />);
    expect(screen.getByText("Chargement des produits…")).toBeTruthy();
  });

  it("affiche la liste des produits de l'API", async () => {
    mockFetch((url) =>
      url.includes("/categories") ? { body: categories } : { body: { items: [product("A-1")], page: 1, size: 20, total: 1 } },
    );
    await render(<ProductListScreen lang="fr" />);
    expect(await screen.findByText("Produit A-1")).toBeTruthy();
    expect(screen.getByText("1 produit")).toBeTruthy();
    expect(screen.getByText(/19,99/)).toBeTruthy();
    expect(screen.getByText("SKU A-1")).toBeTruthy();
  });

  it("filtre par catégorie (A-CAT-01 sur le mobile)", async () => {
    const fetchMock = mockFetch((url) =>
      url.includes("/categories") ? { body: categories } : { body: { items: [], page: 1, size: 20, total: 0 } },
    );
    await render(<ProductListScreen lang="fr" />);
    await fireEvent.press(await screen.findByText("Plomberie"));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u]: [unknown]) => String(u).includes("category_id=c1"))).toBe(true),
    );
    expect(await screen.findByText("Aucun produit dans cette catégorie.")).toBeTruthy();
  });

  it("charge la page suivante", async () => {
    const fetchMock = mockFetch((url) => {
      if (url.includes("/categories")) return { body: categories };
      const page = url.includes("page=2") ? 2 : 1;
      return { body: { items: [product(`P${page}`)], page, size: 20, total: 2 } };
    });
    await render(<ProductListScreen lang="fr" />);
    await fireEvent.press(await screen.findByText("Charger plus"));
    expect(await screen.findByText("Produit P2")).toBeTruthy();
    expect(screen.getByText("Produit P1")).toBeTruthy();
    expect(fetchMock.mock.calls.some(([u]: [unknown]) => String(u).includes("page=2"))).toBe(true);
  });

  it("affiche une erreur réseau et permet de réessayer", async () => {
    let fail = true;
    globalThis.fetch = jest.fn(async (input: unknown) => {
      const url = String(input);
      if (url.includes("/categories")) return { ok: true, status: 200, json: async () => categories } as Response;
      if (fail) throw new TypeError("Network request failed");
      return { ok: true, status: 200, json: async () => ({ items: [product("OK")], page: 1, size: 20, total: 1 }) } as Response;
    }) as unknown as typeof fetch;
    await render(<ProductListScreen lang="fr" />);
    expect(await screen.findByText("Impossible de joindre le serveur. Vérifiez votre connexion.")).toBeTruthy();
    fail = false;
    await fireEvent.press(screen.getByText("Réessayer"));
    expect(await screen.findByText("Produit OK")).toBeTruthy();
  });

  it("affiche les textes et les noms en anglais", async () => {
    mockFetch((url) =>
      url.includes("/categories") ? { body: categories } : { body: { items: [product("E-1")], page: 1, size: 20, total: 1 } },
    );
    await render(<ProductListScreen lang="en" />);
    expect(await screen.findByText("Product E-1")).toBeTruthy();
    expect(screen.getByText("Tools")).toBeTruthy();
    expect(screen.getByText("$19.99")).toBeTruthy();
  });

  it("signale une erreur de l'API", async () => {
    mockFetch((url) =>
      url.includes("/categories")
        ? { body: categories }
        : { status: 500, body: { detail: { code: "internal_error", message: "x" } } },
    );
    await render(<ProductListScreen lang="fr" />);
    expect(await screen.findByText("Impossible de charger le catalogue.")).toBeTruthy();
  });
});
