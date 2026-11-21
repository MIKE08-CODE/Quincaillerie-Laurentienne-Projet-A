/**
 * Configuration par environnement. Expo remplace `process.env.EXPO_PUBLIC_*` au moment du bundle, à
 * partir de .env.development (expo start) ou .env.production (build de production).
 */
const DEFAULT_API_URL = "http://localhost:8000/api/v1";

export function normalizeApiUrl(value: string | undefined): string {
  const url = (value ?? "").trim() || DEFAULT_API_URL;
  return url.replace(/\/+$/, "");
}

export const API_URL = normalizeApiUrl(process.env.EXPO_PUBLIC_API_BASE_URL);
