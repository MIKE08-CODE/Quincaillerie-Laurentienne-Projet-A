import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { authApi, isMfaChallenge } from "../../api/auth";
import { useAuth } from "../../auth/AuthContext";
import { AuthError } from "./AuthError";

/** Connexion (A-AUTH-02), avec la deuxième étape MFA pour le personnel (A-AUTH-06). */
export function LoginPage() {
  const { t } = useTranslation();
  const { signIn, startMfaSetup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function submitPassword(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      const result = await authApi.login(email.trim(), password);
      setPassword(""); // ne pas garder le mot de passe en mémoire plus que nécessaire
      if (isMfaChallenge(result)) {
        setMfaToken(result.mfa_token);
        return;
      }
      if (result.mfa_setup_required) {
        // Personnel sans MFA : le jeton limité ne donne accès qu'à la configuration de la MFA.
        startMfaSetup(result.access_token);
        navigate("/compte/mfa");
        return;
      }
      await signIn(result.access_token);
      navigate("/compte");
    });
  }

  function submitCode(event: FormEvent) {
    event.preventDefault();
    if (!mfaToken) return;
    void run(async () => {
      const result = await authApi.verifyMfa(mfaToken, code);
      await signIn(result.access_token);
      navigate("/compte");
    });
  }

  return (
    <section className="auth">
      <h1>{t("auth.login.title")}</h1>
      {mfaToken ? (
        <form className="form" onSubmit={submitCode}>
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
          <button
            type="submit"
            className="button"
            disabled={busy || code.length !== 6}
          >
            {t("auth.login.verify")}
          </button>
        </form>
      ) : (
        <form className="form" onSubmit={submitPassword}>
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
          <label className="field">
            <span>{t("auth.fields.password")}</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <AuthError error={error} />
          <button type="submit" className="button" disabled={busy}>
            {t("auth.login.submit")}
          </button>
        </form>
      )}
      <p>
        <Link to="/mot-de-passe-oublie">{t("auth.login.forgot")}</Link>
        {" · "}
        <Link to="/inscription">{t("auth.login.register")}</Link>
      </p>
    </section>
  );
}
