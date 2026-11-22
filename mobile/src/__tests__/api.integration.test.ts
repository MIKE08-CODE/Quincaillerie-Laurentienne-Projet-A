/**
 * @jest-environment node
 */
/**
 * Test d'intégration FACULTATIF : le client HTTP de l'application interroge une API réelle.
 *
 *   API_INTEGRATION_URL=http://localhost:8000/api/v1 npm test -- api.integration
 *   API_INTEGRATION_URL=https://quincaillerie-laurentienne-api.onrender.com/api/v1 npm test -- api.integration
 *
 * Sans API_INTEGRATION_URL, le test est ignoré (la CI n'a pas d'API à joindre).
 * La configuration Jest de React Native remplace `fetch` par une simulation : on fournit ici un
 * `fetch` minimal fondé sur le module http de Node, pour que le VRAI code de `getJson` soit exercé.
 */
declare const require: (name: string) => {
  get: (url: string, callback: (res: NodeResponse) => void) => { on: (e: string, cb: (err: Error) => void) => void };
};

interface NodeResponse {
  statusCode?: number;
  setEncoding: (encoding: string) => void;
  on: (event: string, callback: (chunk?: string) => void) => void;
}

function nodeFetch(url: string): Promise<Response> {
  // https pour une API déployée (Render), http pour une API locale.
  const client = require(url.startsWith("https:") ? "node:https" : "node:http");
  return new Promise((resolve, reject) => {
    client
      .get(url, (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          body += chunk ?? "";
        });
        res.on("end", () => {
          const status = res.statusCode ?? 0;
          resolve({ ok: status >= 200 && status < 300, status, json: async () => JSON.parse(body) } as Response);
        });
      })
      .on("error", reject);
  });
}

const url = process.env.API_INTEGRATION_URL;
const maybe = url ? it : it.skip;

interface Page {
  items: { sku: string; name_fr: string; name_en: string; price_cents: number }[];
  total: number;
}

describe("API réelle", () => {
  maybe("renvoie la liste paginée des produits et les catégories", async () => {
    process.env.EXPO_PUBLIC_API_BASE_URL = url;
    globalThis.fetch = ((input: unknown) => nodeFetch(String(input))) as typeof fetch;
    jest.resetModules();
    const { getJson } = jest.requireActual<typeof import("../api/client")>("../api/client");
    const page = await getJson<Page>("/products", { size: 5, sort: "name_asc" });
    expect(page.total).toBeGreaterThanOrEqual(150);
    expect(page.items).toHaveLength(5);
    expect(page.items[0]?.name_en).toBeTruthy();
    const categories = await getJson<unknown[]>("/categories");
    expect(categories.length).toBeGreaterThan(0);
  });
});
