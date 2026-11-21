import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { catalogApi } from "../api/catalog";
import { ProductGrid } from "../components/ProductCard";
import { ErrorMessage, Loading } from "../components/StatusMessage";
import { useApi } from "../hooks/useApi";
import { useReload } from "../hooks/useReload";
import { currentLanguage } from "../i18n";
import { localized } from "../i18n/format";

export function HomePage() {
  const { t } = useTranslation();
  const lang = currentLanguage();
  const [key, reload] = useReload();
  const categories = useApi((s) => catalogApi.categories(s), [key]);
  const newest = useApi((s) => catalogApi.products({ sort: "newest", size: 8 }, s), [key]);

  return (
    <>
      <section className="hero">
        <h1>{t("home.title")}</h1>
        <p>{t("home.intro")}</p>
        <Link to="/produits" className="button">
          {t("home.seeAll")}
        </Link>
      </section>

      <section aria-labelledby="home-categories">
        <h2 id="home-categories">{t("home.categories")}</h2>
        {categories.status === "loading" && <Loading />}
        {categories.status === "error" && <ErrorMessage error={categories.error} onRetry={reload} />}
        {categories.status === "success" && (
          <ul className="chips">
            {categories.data.map((c) => (
              <li key={c.id}>
                <Link to={`/produits?categorie=${c.id}`} className="chip">
                  {localized(c, "name", lang)}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="home-newest">
        <h2 id="home-newest">{t("home.newest")}</h2>
        {newest.status === "loading" && <Loading />}
        {newest.status === "error" && <ErrorMessage error={newest.error} onRetry={reload} />}
        {newest.status === "success" && <ProductGrid products={newest.data.items} />}
      </section>
    </>
  );
}
