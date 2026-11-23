import { type FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { adminApi } from "../../api/admin";
import { useAuth } from "../../auth/AuthContext";
import { AuthError } from "./AuthError";

/**
 * Configuration de la MFA TOTP du personnel (A-AUTH-06), avec le jeton limité reçu à la connexion.
 * La clé n'est affichée qu'ici, n'est jamais stockée par le site et disparaît après l'activation.
 */
export function MfaSetupPage() {
  const { t } = useTranslation();
  const { setupToken, signIn } = useAuth();
  const navigate = useNavigate();
  const [secret, setSecret] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const started = useRef(false); // une seule demande de clé, même en StrictMode

  useEffect(() => {
    if (!setupToken || started.current) return;
    started.current = true;
    adminApi.mfaSetup(setupToken).then(setSecret).catch(setError);
  }, [setupToken]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!setupToken) return;
    setBusy(true);
    setError(null);
    try {
      const result = await adminApi.mfaEnable(setupToken, code);
      setSecret(null);
      await signIn(result.access_token);
      navigate("/compte");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!setupToken) {
    return (
      <section className="auth">
        <h1>{t("mfa.title")}</h1>
        <p>
          {t("mfa.signInFirst")} <Link to="/connexion">{t("auth.login.title")}</Link>
        </p>
      </section>
    );
  }

  return (
    <section className="auth">
      <h1>{t("mfa.title")}</h1>
      <p>{t("mfa.intro")}</p>
      {secret && (
        <dl className="specs">
          <dt>{t("mfa.secret")}</dt>
          <dd>
            <code data-testid="mfa-secret">{secret.secret}</code>
          </dd>
          <dt>{t("mfa.uri")}</dt>
          <dd>
            <code className="mfa__uri">{secret.otpauth_uri}</code>
          </dd>
        </dl>
      )}
      <form className="form" onSubmit={submit}>
        <label className="field">
          <span>{t("auth.fields.mfaCode")}</span>
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
        </label>
        <AuthError error={error} />
        <button type="submit" className="button" disabled={busy || code.length !== 6 || !secret}>
          {t("mfa.enable")}
        </button>
      </form>
    </section>
  );
}
