import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderAt } from "../../test/utils";

type Reply = { status?: number; body?: unknown };
type Call = {
  path: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
  credentials?: string;
};

/** Remplace fetch en enregistrant méthode, corps et en-têtes de chaque appel. */
function mockAuthApi(routes: Record<string, Reply | ((call: Call) => Reply)>) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const call: Call = {
        path: url.pathname,
        method: init?.method ?? "GET",
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
        headers: (init?.headers as Record<string, string>) ?? {},
        credentials: init?.credentials,
      };
      calls.push(call);
      const route = routes[`${call.method} ${call.path}`];
      const reply = typeof route === "function" ? route(call) : route;
      if (!reply)
        return new Response(
          JSON.stringify({ detail: { code: "not_found", message: "x" } }),
          { status: 404 },
        );
      if (reply.status === 204) return new Response(null, { status: 204 });
      return new Response(JSON.stringify(reply.body ?? {}), {
        status: reply.status ?? 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

const error = (status: number, code: string) => ({
  status,
  body: { detail: { code, message: code } },
});
const me = {
  id: "u1",
  email: "marie@example.com",
  first_name: "Marie",
  last_name: "Tremblay",
  language: "fr",
  role: "client",
  is_email_verified: true,
  mfa_enabled: false,
  store_ids: [],
};

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("Inscription (A-AUTH-01)", () => {
  it("envoie le formulaire et affiche le message neutre", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/register": { status: 202, body: { message: "ok" } },
    });
    renderAt("/inscription");
    await userEvent.type(screen.getByLabelText("Prénom"), "Marie");
    await userEvent.type(screen.getByLabelText("Nom"), "Tremblay");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      " marie@example.com ",
    );
    await userEvent.type(
      screen.getByLabelText("Mot de passe"),
      "Scie-a-onglet-2026",
    );
    const submit = screen.getByRole("button", { name: "Créer mon compte" });
    expect(submit).toBeDisabled(); // politique de confidentialité non acceptée
    await userEvent.click(
      screen.getByLabelText(/politique de confidentialité/),
    );
    await userEvent.click(submit);
    expect(
      await screen.findByText(
        /un courriel de vérification vient d'être envoyé/,
      ),
    ).toBeInTheDocument();
    const call = calls.find((c) => c.path === "/api/v1/auth/register");
    expect(call?.body).toMatchObject({
      email: "marie@example.com",
      first_name: "Marie",
      accept_privacy_policy: true,
      marketing_opt_in: false,
      language: "fr",
    });
  });

  it("affiche l'erreur traduite de la politique de mot de passe", async () => {
    mockAuthApi({
      "POST /api/v1/auth/register": error(422, "password_too_short"),
    });
    renderAt("/inscription");
    await userEvent.type(screen.getByLabelText("Prénom"), "Marie");
    await userEvent.type(screen.getByLabelText("Nom"), "Tremblay");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "marie@example.com",
    );
    await userEvent.type(screen.getByLabelText("Mot de passe"), "court");
    await userEvent.click(
      screen.getByLabelText(/politique de confidentialité/),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Créer mon compte" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "au moins 12 caractères",
    );
  });
});

describe("Vérification du courriel (A-AUTH-01)", () => {
  it("lit le jeton dans le fragment, l'envoie une seule fois et l'efface de l'adresse", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/verify-email": { body: { message: "ok" } },
    });
    window.history.replaceState(
      null,
      "",
      "/verifier-courriel#token=jeton-de-test",
    );
    renderAt("/verifier-courriel");
    expect(
      await screen.findByText(/Votre adresse est vérifiée/),
    ).toBeInTheDocument();
    const verify = calls.filter((c) => c.path === "/api/v1/auth/verify-email");
    expect(verify).toHaveLength(1);
    expect(verify[0]?.body).toEqual({ token: "jeton-de-test" });
    expect(window.location.hash).toBe("");
  });

  it("propose de renvoyer le courriel quand le lien est expiré", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/verify-email": error(400, "invalid_or_expired_token"),
      "POST /api/v1/auth/verify-email/resend": {
        status: 202,
        body: { message: "ok" },
      },
    });
    window.history.replaceState(null, "", "/verifier-courriel#token=perime");
    renderAt("/verifier-courriel");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "invalide, expiré ou déjà utilisé",
    );
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "marie@example.com",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: "Renvoyer le courriel de vérification",
      }),
    );
    expect(
      await screen.findByText(/un nouveau courriel vient d'être envoyé/),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/resend"))?.body).toEqual({
      email: "marie@example.com",
    });
  });

  it("signale un lien sans jeton sans appeler l'API de vérification", async () => {
    const calls = mockAuthApi({});
    renderAt("/verifier-courriel");
    expect(
      await screen.findByText("Le lien de vérification est incomplet."),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/v1/auth/verify-email")).toBe(
      false,
    );
  });
});

describe("Connexion et session (A-AUTH-02)", () => {
  it("connecte le client, garde le jeton en mémoire seulement et affiche le compte", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const calls = mockAuthApi({
      "POST /api/v1/auth/login": {
        body: { access_token: "jeton-acces", expires_in: 900 },
      },
      "GET /api/v1/auth/me": { body: me },
      "POST /api/v1/auth/logout": { status: 204 },
    });
    renderAt("/connexion");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "marie@example.com",
    );
    await userEvent.type(
      screen.getByLabelText("Mot de passe"),
      "Scie-a-onglet-2026",
    );
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByText("Bonjour Marie !")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Mon compte" }),
    ).toBeInTheDocument();
    const login = calls.find((c) => c.path === "/api/v1/auth/login");
    expect(login?.credentials).toBe("same-origin"); // cookie httpOnly de rafraîchissement
    expect(
      calls.find((c) => c.path === "/api/v1/auth/me")?.headers.Authorization,
    ).toBe("Bearer jeton-acces");
    const stored = setItem.mock.calls.map(([, value]) => String(value));
    expect(stored.some((value) => value.includes("jeton-acces"))).toBe(false);
    await userEvent.click(
      screen.getByRole("button", { name: "Se déconnecter" }),
    );
    await waitFor(() =>
      expect(calls.some((c) => c.path === "/api/v1/auth/logout")).toBe(true),
    );
    expect(
      await screen.findByRole("heading", { name: "Connexion" }),
    ).toBeInTheDocument();
    setItem.mockRestore();
  });

  it("affiche un message neutre pour des identifiants incorrects", async () => {
    mockAuthApi({
      "POST /api/v1/auth/login": error(401, "invalid_credentials"),
    });
    renderAt("/connexion");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "marie@example.com",
    );
    await userEvent.type(
      screen.getByLabelText("Mot de passe"),
      "mauvais-mot-de-passe",
    );
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Courriel ou mot de passe incorrect.",
    );
  });

  it("signale le verrouillage et la limitation de débit", async () => {
    for (const [status, code, text] of [
      [423, "account_locked", "temporairement bloqué"],
      [429, "rate_limited", "Trop de tentatives"],
    ] as const) {
      mockAuthApi({ "POST /api/v1/auth/login": error(status, code) });
      const { unmount } = renderAt("/connexion");
      await userEvent.type(
        screen.getByLabelText("Courriel"),
        "marie@example.com",
      );
      await userEvent.type(screen.getByLabelText("Mot de passe"), "x");
      await userEvent.click(
        screen.getByRole("button", { name: "Se connecter" }),
      );
      expect(await screen.findByRole("alert")).toHaveTextContent(text);
      unmount();
    }
  });

  it("demande le code MFA pour le personnel puis termine la connexion", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/login": {
        body: { mfa_required: true, mfa_token: "defi" },
      },
      "POST /api/v1/auth/mfa/verify": {
        body: { access_token: "jeton-admin", expires_in: 900 },
      },
      "GET /api/v1/auth/me": {
        body: { ...me, role: "admin", mfa_enabled: true },
      },
    });
    renderAt("/connexion");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "admin@example.com",
    );
    await userEvent.type(
      screen.getByLabelText("Mot de passe"),
      "Scie-a-onglet-2026",
    );
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await userEvent.type(
      await screen.findByLabelText(/Code à 6 chiffres/),
      "12a3456",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Valider le code" }),
    );
    expect(await screen.findByText("Administrateur")).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/mfa/verify"))?.body).toEqual({
      mfa_token: "defi",
      code: "123456",
    });
  });

  it("restaure la session à partir du cookie après un rechargement", async () => {
    mockAuthApi({
      "POST /api/v1/auth/refresh": {
        body: { access_token: "jeton-restaure", expires_in: 900 },
      },
      "GET /api/v1/auth/me": { body: me },
    });
    renderAt("/compte");
    expect(await screen.findByText("Bonjour Marie !")).toBeInTheDocument();
  });

  it("invite à se connecter quand aucune session n'existe", async () => {
    mockAuthApi({
      "POST /api/v1/auth/refresh": error(401, "invalid_refresh_token"),
    });
    renderAt("/compte");
    expect(
      await screen.findByText("Vous n'êtes pas connecté."),
    ).toBeInTheDocument();
  });
});

describe("Réinitialisation du mot de passe (A-AUTH-04)", () => {
  it("demande un lien avec une réponse neutre", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/password/forgot": {
        status: 202,
        body: { message: "ok" },
      },
    });
    renderAt("/mot-de-passe-oublie");
    await userEvent.type(
      screen.getByLabelText("Courriel"),
      "inconnu@example.com",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: "Recevoir un lien de réinitialisation",
      }),
    );
    expect(
      await screen.findByText(/Si un compte existe pour cette adresse/),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/forgot"))?.body).toEqual({
      email: "inconnu@example.com",
    });
  });

  it("enregistre le nouveau mot de passe avec le jeton du fragment", async () => {
    const calls = mockAuthApi({
      "POST /api/v1/auth/password/reset": { body: { message: "ok" } },
    });
    window.history.replaceState(
      null,
      "",
      "/reinitialiser-mot-de-passe#token=jeton-reinit",
    );
    renderAt("/reinitialiser-mot-de-passe");
    expect(window.location.hash).toBe("");
    await userEvent.type(
      screen.getByLabelText("Nouveau mot de passe"),
      "Niveau-a-bulle-2026",
    );
    await userEvent.type(
      screen.getByLabelText("Confirmer le mot de passe"),
      "Niveau-a-bulle-2026",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Enregistrer le mot de passe" }),
    );
    expect(
      await screen.findByText(/Votre mot de passe a été modifié/),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/reset"))?.body).toEqual({
      token: "jeton-reinit",
      new_password: "Niveau-a-bulle-2026",
    });
  });

  it("refuse deux mots de passe différents sans appeler l'API", async () => {
    const calls = mockAuthApi({});
    window.history.replaceState(
      null,
      "",
      "/reinitialiser-mot-de-passe#token=jeton",
    );
    renderAt("/reinitialiser-mot-de-passe");
    await userEvent.type(
      screen.getByLabelText("Nouveau mot de passe"),
      "Niveau-a-bulle-2026",
    );
    await userEvent.type(
      screen.getByLabelText("Confirmer le mot de passe"),
      "Autre-chose-2026",
    );
    expect(
      screen.getByText("Les deux mots de passe ne correspondent pas."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Enregistrer le mot de passe" }),
    ).toBeDisabled();
    expect(calls).toHaveLength(0);
  });

  it("explique qu'un lien expiré doit être redemandé", async () => {
    mockAuthApi({
      "POST /api/v1/auth/password/reset": error(
        400,
        "invalid_or_expired_token",
      ),
    });
    window.history.replaceState(
      null,
      "",
      "/reinitialiser-mot-de-passe#token=perime",
    );
    renderAt("/reinitialiser-mot-de-passe");
    await userEvent.type(
      screen.getByLabelText("Nouveau mot de passe"),
      "Niveau-a-bulle-2026",
    );
    await userEvent.type(
      screen.getByLabelText("Confirmer le mot de passe"),
      "Niveau-a-bulle-2026",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Enregistrer le mot de passe" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "invalide, expiré ou déjà utilisé",
    );
  });

  it("indique qu'un lien sans jeton est incomplet", () => {
    mockAuthApi({});
    renderAt("/reinitialiser-mot-de-passe");
    expect(
      screen.getByText(/incomplet ou a déjà été utilisé/),
    ).toBeInTheDocument();
  });
});
