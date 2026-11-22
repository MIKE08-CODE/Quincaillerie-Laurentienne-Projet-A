/** Appels d'authentification (A-AUTH-01 à 04) vers /api/v1/auth. */
import { sendJson } from "./client";

export interface MessageResponse {
  message: string;
}

export interface TokenResponse {
  access_token: string;
  token_type?: string;
  expires_in: number;
  mfa_setup_required?: boolean;
}

export interface MfaChallenge {
  mfa_required?: boolean;
  mfa_token: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  language: "fr" | "en";
  role: "client" | "clerk" | "manager" | "admin";
  is_email_verified: boolean;
  mfa_enabled: boolean;
  store_ids: string[];
}

export interface RegisterInput {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  language: "fr" | "en";
  accept_privacy_policy: true;
  marketing_opt_in: boolean;
}

export function isMfaChallenge(
  result: TokenResponse | MfaChallenge,
): result is MfaChallenge {
  return "mfa_token" in result;
}

export const authApi = {
  register: (input: RegisterInput) =>
    sendJson<MessageResponse>("/auth/register", input),
  verifyEmail: (token: string) =>
    sendJson<MessageResponse>("/auth/verify-email", { token }),
  resendVerification: (email: string) =>
    sendJson<MessageResponse>("/auth/verify-email/resend", { email }),
  login: (email: string, password: string) =>
    sendJson<TokenResponse | MfaChallenge>("/auth/login", { email, password }),
  verifyMfa: (mfaToken: string, code: string) =>
    sendJson<TokenResponse>("/auth/mfa/verify", { mfa_token: mfaToken, code }),
  refresh: () => sendJson<TokenResponse>("/auth/refresh"),
  me: (token: string) =>
    sendJson<CurrentUser>("/auth/me", undefined, { method: "GET", token }),
  logout: (token?: string) =>
    sendJson<void>("/auth/logout", undefined, { token }),
  forgotPassword: (email: string) =>
    sendJson<MessageResponse>("/auth/password/forgot", { email }),
  resetPassword: (token: string, newPassword: string) =>
    sendJson<MessageResponse>("/auth/password/reset", {
      token,
      new_password: newPassword,
    }),
};

/**
 * Lit le jeton à usage unique placé dans le FRAGMENT de l'URL (`#token=...`) par le lien du courriel.
 * Le fragment n'est jamais envoyé au serveur ni dans l'en-tête Referer; il est effacé de la barre
 * d'adresse dès sa lecture.
 */
export function takeTokenFromHash(): string | null {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = params.get("token");
  if (token) {
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search,
    );
  }
  return token && token.length <= 2048 ? token : null;
}
