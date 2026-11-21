import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { AppRoutes } from "../routes/AppRoutes";

type Handler = (url: URL) => { status?: number; body: unknown } | undefined;

/** Remplace fetch : chaque appel est passé au gestionnaire, qui renvoie statut et corps JSON. */
export function mockApi(handler: Handler) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "http://localhost");
    const result = handler(url);
    if (!result) return new Response(JSON.stringify({ detail: { code: "not_found", message: "x" } }), { status: 404 });
    return new Response(JSON.stringify(result.body), {
      status: result.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

export const product = (overrides: Record<string, unknown> = {}) => ({
  id: "11111111-1111-4111-8111-111111111111",
  sku: "PERC-18V",
  name_fr: "Perceuse-visseuse sans fil 18 V",
  name_en: "Cordless drill driver 18 V",
  brand: "Laurentide Pro",
  price_cents: 12999,
  main_image_url: "https://images.example/perc-18v.jpg",
  category_id: "c1",
  ...overrides,
});

export const page = (items: unknown[], total = items.length, pageNumber = 1, size = 24) => ({
  items,
  page: pageNumber,
  size,
  total,
});

export const categories = [
  {
    id: "c0",
    slug: "outils",
    name_fr: "Outils",
    name_en: "Tools",
    children: [{ id: "c1", slug: "perceuses", name_fr: "Perceuses", name_en: "Drills", children: [] }],
  },
];
