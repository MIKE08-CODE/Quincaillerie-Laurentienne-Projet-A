import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { authApi } from "../../api/auth";
import { currentLanguage } from "../../i18n";
import { AuthError } from "./AuthError";

/** Inscription du client (A-AUTH-01). La réponse est identique que l'adresse soit libre ou non. */
export function RegisterPage() {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });
  const [accept, setAccept] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!accept) return;
    setBusy(true);
    setError(null);
    try {
      await authApi.register({
        ...form,
        email: form.email.trim(),
        language: currentLanguage(),
        accept_privacy_policy: true,
        marketing_opt_in: marketing,
      });
      setDone(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <section className="auth">
        <h1>{t("auth.register.title")}</h1>
        <p role="status">{t("auth.register.done")}</p>
      </section>
    );
  }

  const field = (
    name: keyof typeof form,
    type = "text",
    autoComplete?: string,
  ) => (
    <label className="field">
      <span>{t(`auth.fields.${name}`)}</span>
      <input
        type={type}
        required
        autoComplete={autoComplete}
        maxLength={name === "password" ? 128 : 254}
        value={form[name]}
        onChange={(e) => setForm({ ...form, [name]: e.target.value })}
      />
    </label>
  );

  return (
    <section className="auth">
      <h1>{t("auth.register.title")}</h1>
      <form className="form" onSubmit={submit} noValidate={false}>
        {field("first_name", "text", "given-name")}
        {field("last_name", "text", "family-name")}
        {field("email", "email", "email")}
        {field("password", "password", "new-password")}
        <p className="field__hint">{t("auth.register.passwordHint")}</p>
        <label className="checkbox">
          <input
            type="checkbox"
            required
            checked={accept}
            onChange={(e) => setAccept(e.target.checked)}
          />
          <span>
            {t("auth.register.acceptPrivacy")}{" "}
            <Link to="/confidentialite" target="_blank" rel="noopener">
              {t("auth.register.privacyLink")}
            </Link>
          </span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={marketing}
            onChange={(e) => setMarketing(e.target.checked)}
          />
          <span>{t("auth.register.marketing")}</span>
        </label>
        <AuthError error={error} />
        <button type="submit" className="button" disabled={busy || !accept}>
          {t("auth.register.submit")}
        </button>
      </form>
      <p>
        <Link to="/connexion">{t("auth.register.haveAccount")}</Link>
      </p>
    </section>
  );
}
