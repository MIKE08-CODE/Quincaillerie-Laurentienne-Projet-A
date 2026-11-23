import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function MainLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [query, setQuery] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (q) navigate(`/recherche?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header__top">
          <Link to="/" className="header__brand">
            {t("brand")}
          </Link>
          <button
            type="button"
            className="button button--ghost"
            aria-label={t("language.label")}
            onClick={() => void i18n.changeLanguage(i18n.language === "en" ? "fr" : "en")}
          >
            {t("language.switch")}
          </button>
        </div>
        <form className="search" role="search" onSubmit={submit}>
          <label htmlFor="search-input" className="visually-hidden">
            {t("search.label")}
          </label>
          <input
            id="search-input"
            type="search"
            value={query}
            maxLength={100}
            placeholder={t("search.placeholder")}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="button">
            {t("search.submit")}
          </button>
        </form>
        <nav className="nav">
          <NavLink to="/" end>
            {t("nav.home")}
          </NavLink>
          <NavLink to="/produits">{t("nav.catalog")}</NavLink>
          <NavLink to="/magasins">{t("nav.stores")}</NavLink>
          <NavLink to={user ? "/compte" : "/connexion"}>{user ? t("nav.account") : t("nav.login")}</NavLink>
          {user?.role === "admin" && <NavLink to="/admin">{t("nav.admin")}</NavLink>}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        {t("footer")} <Link to="/confidentialite">{t("nav.privacy")}</Link>
      </footer>
    </div>
  );
}
