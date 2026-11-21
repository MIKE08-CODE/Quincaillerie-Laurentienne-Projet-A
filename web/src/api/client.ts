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
