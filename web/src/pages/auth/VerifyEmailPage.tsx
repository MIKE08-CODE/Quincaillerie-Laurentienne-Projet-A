import { type FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { authApi, takeTokenFromHash } from "../../api/auth";
import { AuthError } from "./AuthError";

type State = "verifying" | "verified" | "failed" | "missing";

/** Lien du courriel de vérification (A-AUTH-01) : /verifier-courriel#token=... */
export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [state, setState] = useState<State>("verifying");
  const [error, setError] = useState<unknown>(null);
  const [email, setEmail] = useState("");
  const [resent, setResent] = useState(false);
  const started = useRef(false); // un jeton est à usage unique : un seul envoi, même en StrictMode

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = takeTokenFromHash();
    if (!token) {
      setState("missing");
      return;
    }
    authApi
      .verifyEmail(token)
      .then(() => setState("verified"))
      .catch((err: unknown) => {
        setError(err);
        setState("failed");
      });
  }, []);

  async function resend(event: FormEvent) {
    event.preventDefault();
    try {
      await authApi.resendVerification(email.trim());
      setResent(true);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section className="auth">
      <h1>{t("auth.verify.title")}</h1>
      {state === "verifying" && (
        <p role="status">{t("auth.verify.verifying")}</p>
      )}
      {state === "verified" && (
        <p role="status">
          {t("auth.verify.verified")}{" "}
          <Link to="/connexion">{t("auth.login.title")}</Link>
        </p>
      )}
      {(state === "failed" || state === "missing") && (
        <>
          {state === "failed" ? (
            <AuthError error={error} />
          ) : (
            <p role="alert">{t("auth.verify.missing")}</p>
          )}
          {resent ? (
            <p role="status">{t("auth.verify.resent")}</p>
          ) : (
            <form className="form" onSubmit={resend}>
              <label className="field">
                <span>{t("auth.fields.email")}</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <button type="submit" className="button">
                {t("auth.verify.resend")}
              </button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
