import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { catalogApi, type ProductSort } from "../api/catalog";
import { CategoryTree } from "../components/CategoryTree";
import { Pagination } from "../components/Pagination";
import { ProductGrid } from "../components/ProductCard";
import { Empty, ErrorMessage, Loading } from "../components/StatusMessage";
import { useApi } from "../hooks/useApi";
import { useReload } from "../hooks/useReload";
import { currentLanguage } from "../i18n";

export const PAGE_SIZE = 24;
const SORTS: ProductSort[] = ["newest", "price_asc", "price_desc", "name_asc", "name_desc"];

function readSort(value: string | null): ProductSort {
  return SORTS.includes(value as ProductSort) ? (value as ProductSort) : "newest";
}

function readPage(value: string | null): number {
  const page = Number(value);
  return Number.isInteger(page) && page >= 1 ? page : 1;
}

export function CatalogPage() {
  const { t } = useTranslation();
  const lang = currentLanguage();
  const [params, setParams] = useSearchParams();
  const category = params.get("categorie");
  const sort = readSort(params.get("tri"));
  const page = readPage(params.get("page"));
  const [key, reload] = useReload();

  const categories = useApi((s) => catalogApi.categories(s), []);
  const products = useApi(
    (s) =>
      catalogApi.products({ page, size: PAGE_SIZE, sort, lang, category_id: category ?? undefined }, s),
    [page, sort, lang, category, key],
  );

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [name, value] of Object.entries(changes)) {
      if (value === null) next.delete(name);
      else next.set(name, value);
    }
    if (!("page" in changes)) next.delete("page"); // nouveau filtre ou tri : retour à la page 1
    setParams(next);
  }

  return (
    <div className="catalog">
      <aside className="catalog__aside">
        {categories.status === "success" && (
          <CategoryTree nodes={categories.data} selected={category} onSelect={(id) => update({ categorie: id })} />
        )}
        {categories.status === "error" && <ErrorMessage error={categories.error} />}
      </aside>

      <section className="catalog__content">
        <div className="toolbar">
          <h1>{t("catalog.title")}</h1>
          <label className="toolbar__sort">
            {t("catalog.sort")}
            <select value={sort} onChange={(e) => update({ tri: e.target.value })}>
              {SORTS.map((s) => (
                <option key={s} value={s}>
                  {t(`catalog.sorts.${s}`)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {products.status === "loading" && <Loading />}
        {products.status === "error" && <ErrorMessage error={products.error} onRetry={reload} />}
        {products.status === "success" && (
          <>
            <p className="toolbar__count">{t("catalog.count", { count: products.data.total })}</p>
            {products.data.items.length === 0 ? (
              <Empty message={t("catalog.empty")} />
            ) : (
              <ProductGrid products={products.data.items} />
            )}
            <Pagination
              page={page}
              size={PAGE_SIZE}
              total={products.data.total}
              onChange={(p) => update({ page: String(p) })}
            />
          </>
        )}
      </section>
    </div>
  );
}
