import { useTranslation } from "react-i18next";

import { ApiError } from "../../api/client";

const KNOWN = new Set([
  "invalid_credentials",
  "account_locked",
  "email_not_verified",
  "invalid_or_expired_token",
  "invalid_mfa_code",
  "invalid_mfa_token",
  "rate_limited",
  "network_error",
  "password_too_short",
  "password_too_long",
  "password_too_common",
  "password_too_simple",
  "password_contains_personal_info",
]);

/** Message d'erreur traduit d'après le `code` stable de l'API; repli sur un message générique. */
export function AuthError({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  const code = error instanceof ApiError ? error.code : "unknown";
  return (
    <p className="status status--error" role="alert">
      {t(KNOWN.has(code) ? `auth.errors.${code}` : "auth.errors.generic")}
    </p>
  );
}
