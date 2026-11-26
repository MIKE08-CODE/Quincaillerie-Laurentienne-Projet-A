import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { authApi, takeTokenFromHash } from "../../api/auth";
import { AuthError } from "./AuthError";

/** Demande de réinitialisation (A-AUTH-04) : même réponse que l'adresse existe ou non. */
export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.forgotPassword(email.trim());
      setDone(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth">
      <h1>{t("auth.forgot.title")}</h1>
      {done ? (
        <p role="status">{t("auth.forgot.done")}</p>
      ) : (
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>{t("auth.fields.email")}</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <AuthError error={error} />
          <button type="submit" className="button" disabled={busy}>
            {t("auth.forgot.submit")}
          </button>
        </form>
      )}
    </section>
  );
}

/** Lien du courriel de réinitialisation : /reinitialiser-mot-de-passe#token=... (30 minutes, usage unique). */
export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [token] = useState(() => takeTokenFromHash());
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const mismatch = confirm.length > 0 && password !== confirm;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token || mismatch) return;
    setBusy(true);
    setError(null);
    try {
      await authApi.resetPassword(token, password);
      setPassword("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <section className="auth">
        <h1>{t("auth.reset.title")}</h1>
        <p role="alert">{t("auth.reset.missing")}</p>
        <Link to="/mot-de-passe-oublie">{t("auth.forgot.title")}</Link>
      </section>
    );
  }

  return (
    <section className="auth">
      <h1>{t("auth.reset.title")}</h1>
      {done ? (
        <p role="status">
          {t("auth.reset.done")}{" "}
          <Link to="/connexion">{t("auth.login.title")}</Link>
        </p>
      ) : (
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>{t("auth.fields.newPassword")}</span>
            <input
              type="password"
              autoComplete="new-password"
              required
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label className="field">
            <span>{t("auth.fields.confirmPassword")}</span>
            <input
              type="password"
              autoComplete="new-password"
              required
              maxLength={128}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </label>
          <p className="field__hint">{t("auth.register.passwordHint")}</p>
          {mismatch && <p role="alert">{t("auth.reset.mismatch")}</p>}
          <AuthError error={error} />
          <button type="submit" className="button" disabled={busy || mismatch}>
            {t("auth.reset.submit")}
          </button>
        </form>
      )}
    </section>
  );
}
