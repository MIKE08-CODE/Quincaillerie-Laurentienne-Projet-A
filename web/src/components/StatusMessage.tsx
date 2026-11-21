import { useTranslation } from "react-i18next";

import type { ApiError } from "../api/client";

export function Loading() {
  const { t } = useTranslation();
  return (
    <p className="status status--loading" role="status" aria-live="polite">
      {t("state.loading")}
    </p>
  );
}

export function ErrorMessage({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const { t } = useTranslation();
  const key = ["network_error", "rate_limited"].includes(error.code) ? `state.${error.code}` : "state.error";
  return (
    <div className="status status--error" role="alert">
      <p>{t(key)}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          {t("state.retry")}
        </button>
      )}
    </div>
  );
}

export function Empty({ message }: { message: string }) {
  return <p className="status status--empty">{message}</p>;
}
