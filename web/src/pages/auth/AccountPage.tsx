import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import { Loading } from "../../components/StatusMessage";

/** Compte connecté : prouve la session (A-AUTH-02) et permet de se déconnecter. */
export function AccountPage() {
  const { t } = useTranslation();
  const { user, restore, signOut } = useAuth();
  const navigate = useNavigate();
  const [checking, setChecking] = useState(!user);
  const tried = useRef(false);

  useEffect(() => {
    if (user || tried.current) return;
    tried.current = true;
    void restore().finally(() => setChecking(false));
  }, [user, restore]);

  if (checking) return <Loading />;
  if (!user) {
    return (
      <section className="auth">
        <h1>{t("auth.account.title")}</h1>
        <p>
          {t("auth.account.signedOut")}{" "}
          <Link to="/connexion">{t("auth.login.title")}</Link>
        </p>
      </section>
    );
  }

  return (
    <section className="auth">
      <h1>{t("auth.account.title")}</h1>
      <p>{t("auth.account.hello", { name: user.first_name })}</p>
      <dl className="specs">
        <dt>{t("auth.fields.email")}</dt>
        <dd>{user.email}</dd>
        <dt>{t("auth.account.role")}</dt>
        <dd>{t(`auth.roles.${user.role}`)}</dd>
      </dl>
      {user.role === "admin" && (
        <p>
          <Link to="/admin">{t("admin.title")}</Link>
        </p>
      )}
      <button
        type="button"
        className="button"
        onClick={() => void signOut().then(() => navigate("/connexion"))}
      >
        {t("auth.account.logout")}
      </button>
    </section>
  );
}
