import { API_URL } from "../config";

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

export type QueryValue = string | number | undefined | null;

export function buildUrl(path: string, params: Record<string, QueryValue> = {}, base = API_URL): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return `${base}${path}${parts.length ? `?${parts.join("&")}` : ""}`;
}

/**
 * Délai maximal d'une requête. L'offre gratuite de Render met l'API en veille après 15 minutes
 * d'inactivité; son réveil prend jusqu'à une minute environ : un délai plus court ferait échouer le
 * premier chargement (« API injoignable ») alors que l'API répond quelques secondes plus tard.
 */
export const API_TIMEOUT_MS = 60_000;

/** GET JSON avec délai maximal : une API injoignable donne une erreur claire au lieu d'attendre. */
export async function getJson<T>(
  path: string,
  params: Record<string, QueryValue> = {},
  timeoutMs = API_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "network_error", "API injoignable");
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    let code = `http_${response.status}`;
    try {
      const body = (await response.json()) as { detail?: { code?: string } };
      code = body.detail?.code ?? code;
    } catch {
      // corps non JSON
    }
    throw new ApiError(response.status, code, code);
  }
  return (await response.json()) as T;
}
