import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderAt } from "../../test/utils";

type Reply = { status?: number; body?: unknown };
type Call = { path: string; method: string; body: unknown; headers: Record<string, string>; search: string };

function mockApi(routes: Record<string, Reply | ((call: Call) => Reply)>) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const raw = init?.body;
      const call: Call = {
        path: url.pathname,
        search: url.search,
        method: init?.method ?? "GET",
        body: typeof raw === "string" ? JSON.parse(raw) : raw,
        headers: (init?.headers as Record<string, string>) ?? {},
      };
      calls.push(call);
      const route = routes[`${call.method} ${call.path}`];
      const reply = typeof route === "function" ? route(call) : route;
      if (!reply) return new Response(JSON.stringify({ detail: { code: "not_found", message: "x" } }), { status: 404 });
      if (reply.status === 204) return new Response(null, { status: 204 });
      return new Response(JSON.stringify(reply.body ?? {}), {
        status: reply.status ?? 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

const error = (status: number, code: string) => ({ status, body: { detail: { code, message: code } } });
const admin = {
  id: "a1",
  email: "admin@example.com",
  first_name: "Alex",
  last_name: "Admin",
  language: "fr",
  role: "admin",
  is_email_verified: true,
  mfa_enabled: true,
  store_ids: [],
};
const product = {
  id: "p1",
  sku: "PERC-18V",
  name_fr: "Perceuse 18 V",
  name_en: "Drill 18 V",
  price_cents: 12999,
  is_active: true,
  images: [{ id: "i1", url: "https://images.example.com/a.jpg", alt_fr: null, alt_en: null, position: 0 }],
};
const signedInAdmin = {
  "POST /api/v1/auth/refresh": { body: { access_token: "jeton-admin", expires_in: 900 } },
  "GET /api/v1/auth/me": { body: admin },
  "GET /api/v1/admin/products": { body: { items: [product], page: 1, size: 20, total: 1 } },
};

describe("MFA du personnel (A-AUTH-06)", () => {
  it("guide le personnel sans MFA vers la configuration, sans appeler /me avec le jeton limité", async () => {
    const calls = mockApi({
      "POST /api/v1/auth/login": { body: { access_token: "jeton-limite", expires_in: 900, mfa_setup_required: true } },
      "POST /api/v1/auth/mfa/setup": { body: { secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/QL:admin" } },
      "POST /api/v1/auth/mfa/enable": { body: { access_token: "jeton-complet", expires_in: 900 } },
      "GET /api/v1/auth/me": (c) =>
        c.headers.Authorization === "Bearer jeton-complet" ? { body: admin } : error(403, "mfa_required"),
    });
    renderAt("/connexion");
    await userEvent.type(screen.getByLabelText("Courriel"), "admin@example.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "Scie-a-onglet-2026");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByTestId("mfa-secret")).toHaveTextContent("JBSWY3DPEHPK3PXP");
    expect(calls.find((c) => c.path.endsWith("/mfa/setup"))?.headers.Authorization).toBe("Bearer jeton-limite");
    await userEvent.type(screen.getByLabelText(/Code à 6 chiffres/), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Activer" }));
    expect(await screen.findByRole("link", { name: "Administration du catalogue" })).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/mfa/enable"))?.body).toEqual({ code: "123456" });
    expect(calls.filter((c) => c.path.endsWith("/auth/me")).map((c) => c.headers.Authorization)).toEqual([
      "Bearer jeton-complet",
    ]);
  });

  it("refuse un code MFA incorrect avec un message clair", async () => {
    mockApi({
      "POST /api/v1/auth/login": { body: { access_token: "jeton-limite", expires_in: 900, mfa_setup_required: true } },
      "POST /api/v1/auth/mfa/setup": { body: { secret: "ABC", otpauth_uri: "otpauth://totp/x" } },
      "POST /api/v1/auth/mfa/enable": error(401, "invalid_mfa_code"),
    });
    renderAt("/connexion");
    await userEvent.type(screen.getByLabelText("Courriel"), "admin@example.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await screen.findByTestId("mfa-secret");
    await userEvent.type(screen.getByLabelText(/Code à 6 chiffres/), "000000");
    await userEvent.click(screen.getByRole("button", { name: "Activer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Code incorrect.");
  });

  it("demande de se connecter quand on ouvre la page sans jeton limité", () => {
    mockApi({});
    renderAt("/compte/mfa");
    expect(screen.getByText(/Connectez-vous d'abord/)).toBeInTheDocument();
  });
});

describe("Administration du catalogue (A-ADM-01)", () => {
  it("invite à se connecter sans session et refuse un client", async () => {
    mockApi({ "POST /api/v1/auth/refresh": error(401, "invalid_refresh_token") });
    const { unmount } = renderAt("/admin");
    expect(await screen.findByText(/Connectez-vous avec un compte administrateur/)).toBeInTheDocument();
    unmount();
    mockApi({
      "POST /api/v1/auth/refresh": { body: { access_token: "jeton-client", expires_in: 900 } },
      "GET /api/v1/auth/me": { body: { ...admin, role: "client" } },
    });
    renderAt("/admin");
    expect(await screen.findByRole("alert")).toHaveTextContent("réservée aux administrateurs");
  });

  it("liste les produits et enregistre le nom, le prix et l'activation", async () => {
    const calls = mockApi({
      ...signedInAdmin,
      "PATCH /api/v1/admin/products/p1": { body: { ...product, price_cents: 10950, is_active: false } },
    });
    renderAt("/admin");
    expect(await screen.findByText("Perceuse 18 V")).toBeInTheDocument();
    expect(screen.getByText("1 produits (actifs et désactivés)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Modifier PERC-18V" }));
    const price = screen.getByLabelText("Prix ($)");
    await userEvent.clear(price);
    await userEvent.type(price, "109,50");
    await userEvent.click(screen.getByLabelText("Visible dans le catalogue"));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Produit enregistré.")).toBeInTheDocument();
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.body).toEqual({ name_fr: "Perceuse 18 V", name_en: "Drill 18 V", price_cents: 10950, is_active: false });
    expect(patch?.headers.Authorization).toBe("Bearer jeton-admin");
  });

  it("téléverse une image avec son type et le jeton, puis la retire", async () => {
    const calls = mockApi({
      ...signedInAdmin,
      "POST /api/v1/admin/products/p1/images/upload": {
        status: 201,
        body: { id: "i2", url: "https://res.cloudinary.com/x/a.png", alt_fr: null, alt_en: null, position: 1 },
      },
      "DELETE /api/v1/admin/products/p1/images/i1": { status: 204 },
    });
    renderAt("/admin");
    await userEvent.click(await screen.findByRole("button", { name: "Modifier PERC-18V" }));
    const file = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "perceuse.png", { type: "image/png" });
    await userEvent.upload(screen.getByLabelText("Nouvelle image"), file);
    await userEvent.click(screen.getByRole("button", { name: "Téléverser l'image" }));
    expect(await screen.findByText("Image ajoutée.")).toBeInTheDocument();
    const upload = calls.find((c) => c.path.endsWith("/images/upload"));
    expect(upload?.headers["Content-Type"]).toBe("image/png");
    expect(upload?.headers.Authorization).toBe("Bearer jeton-admin");
    expect(upload?.body).toBe(file);
    expect(upload?.search).toContain("alt_fr=Perceuse");
    await userEvent.click(screen.getByRole("button", { name: "Retirer" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
  });

  it("explique que le téléversement n'est pas encore activé (503)", async () => {
    mockApi({
      ...signedInAdmin,
      "POST /api/v1/admin/products/p1/images/upload": error(503, "image_storage_not_configured"),
    });
    renderAt("/admin");
    await userEvent.click(await screen.findByRole("button", { name: "Modifier PERC-18V" }));
    await userEvent.upload(screen.getByLabelText("Nouvelle image"), new File(["x"], "a.png", { type: "image/png" }));
    await userEvent.click(screen.getByRole("button", { name: "Téléverser l'image" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("pas encore activé");
  });

  it("refuse un prix invalide sans appeler l'API", async () => {
    const calls = mockApi(signedInAdmin);
    renderAt("/admin");
    await userEvent.click(await screen.findByRole("button", { name: "Modifier PERC-18V" }));
    const price = screen.getByLabelText("Prix ($)");
    await userEvent.clear(price);
    await userEvent.type(price, "abc");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PATCH")).toBe(false);
  });
});

describe("Politique de confidentialité (ébauche)", () => {
  it("affiche clairement que le texte est à valider", () => {
    mockApi({});
    renderAt("/confidentialite");
    expect(screen.getByRole("note")).toHaveTextContent("ÉBAUCHE À VALIDER");
    expect(screen.getByRole("heading", { name: "Politique de confidentialité" })).toBeInTheDocument();
    expect(screen.getAllByText(/À compléter/).length).toBeGreaterThan(0);
  });

  it("est accessible depuis le formulaire d'inscription et le pied de page", () => {
    mockApi({});
    renderAt("/inscription");
    const link = screen.getByRole("link", { name: /politique de confidentialité \(ébauche à valider\)/ });
    expect(link).toHaveAttribute("href", "/confidentialite");
    expect(screen.getByRole("link", { name: "Confidentialité" })).toHaveAttribute("href", "/confidentialite");
  });
});
