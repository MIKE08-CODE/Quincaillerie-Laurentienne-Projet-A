import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { catalogApi } from "../api/catalog";
import { Pagination } from "../components/Pagination";
import { ProductGrid } from "../components/ProductCard";
import { Empty, ErrorMessage, Loading } from "../components/StatusMessage";
import { useApi } from "../hooks/useApi";
import { useReload } from "../hooks/useReload";
import { PAGE_SIZE } from "./CatalogPage";

export function SearchPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [key, reload] = useReload();
  const results = useApi(
    (s) => (q ? catalogApi.search(q, page, PAGE_SIZE, s) : Promise.resolve(null)),
    [q, page, key],
  );

  if (!q) return <Empty message={t("search.prompt")} />;

  return (
    <section>
      <h1>{t("search.title", { q })}</h1>
      {results.status === "loading" && <Loading />}
      {results.status === "error" && <ErrorMessage error={results.error} onRetry={reload} />}
      {results.status === "success" && results.data && (
        <>
          {results.data.items.length === 0 ? (
            <Empty message={t("search.empty", { q })} />
          ) : (
            <>
              <p className="toolbar__count">{t("catalog.count", { count: results.data.total })}</p>
              <ProductGrid products={results.data.items} />
            </>
          )}
          <Pagination
            page={page}
            size={PAGE_SIZE}
            total={results.data.total}
            onChange={(p) => setParams({ q, page: String(p) })}
          />
        </>
      )}
    </section>
  );
}
