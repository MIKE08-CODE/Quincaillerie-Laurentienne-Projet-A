/**
 * Client HTTP minimal vers l'API FastAPI (/api/v1).
 *
 * - L'URL de base vient de VITE_API_BASE_URL (par défaut « /api/v1 », même origine que le site).
 * - Les erreurs de l'API ont la forme {"detail": {"code", "message"}} : le `code` stable est conservé
 *   pour afficher un message traduit.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type QueryValue = string | number | boolean | null | undefined;

export function buildUrl(path: string, params: Record<string, QueryValue> = {}): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const search = query.toString();
  return `${API_BASE_URL}${path}${search ? `?${search}` : ""}`;
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (detail && typeof detail === "object" && "code" in detail) {
      const { code, message } = detail as { code: string; message?: string };
      return new ApiError(response.status, code, message ?? code);
    }
  } catch {
    // corps absent ou non JSON : on retombe sur un code générique
  }
  return new ApiError(response.status, `http_${response.status}`, response.statusText || "Erreur");
}

export async function getJson<T>(
  path: string,
  params: Record<string, QueryValue> = {},
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { headers: { Accept: "application/json" }, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "API injoignable");
  }
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

/**
 * Requête POST (ou autre) avec un corps JSON. `credentials: "same-origin"` joint le cookie httpOnly
 * de rafraîchissement (même origine grâce au relais Vercel). Le jeton d'accès, s'il est fourni, est
 * envoyé dans l'en-tête Authorization; il n'est jamais stocké par ce module.
 */
export async function sendJson<T>(
  path: string,
  body?: unknown,
  { method = "POST", token }: { method?: string; token?: string } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "network_error", "API injoignable");
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Envoi d'un fichier brut (téléversement d'image) avec son type ; jeton d'accès obligatoire. */
export async function sendFile<T>(path: string, file: Blob, token: string, params: Record<string, QueryValue> = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      method: "POST",
      headers: { Accept: "application/json", Authorization: `Bearer ${token}`, "Content-Type": file.type },
      body: file,
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "network_error", "API injoignable");
  }
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

/** GET JSON authentifié (routes d'administration). */
export async function getJsonAuth<T>(path: string, token: string, params: Record<string, QueryValue> = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "network_error", "API injoignable");
  }
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}
