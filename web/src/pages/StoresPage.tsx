import { useTranslation } from "react-i18next";

import { catalogApi } from "../api/catalog";
import { ErrorMessage, Loading } from "../components/StatusMessage";
import { useApi } from "../hooks/useApi";
import { useReload } from "../hooks/useReload";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

export function StoresPage() {
  const { t } = useTranslation();
  const [key, reload] = useReload();
  const stores = useApi((s) => catalogApi.stores(s), [key]);

  return (
    <section>
      <h1>{t("stores.title")}</h1>
      {stores.status === "loading" && <Loading />}
      {stores.status === "error" && <ErrorMessage error={stores.error} onRetry={reload} />}
      {stores.status === "success" && (
        <ul className="stores">
          {stores.data.map((store) => (
            <li key={store.id} className="store">
              <h2>{store.name}</h2>
              <p>{store.address}</p>
              {store.phone && (
                <p>
                  {t("stores.phone")} : <a href={`tel:${store.phone}`}>{store.phone}</a>
                </p>
              )}
              <h3>{t("stores.hours")}</h3>
              <dl className="hours">
                {DAYS.filter((d) => store.opening_hours[d]).map((d) => (
                  <div key={d}>
                    <dt>{t(`days.${d}`)}</dt>
                    <dd>{store.opening_hours[d]?.join(" – ")}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
