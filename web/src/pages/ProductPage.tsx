import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { catalogApi } from "../api/catalog";
import { AvailabilityBadge } from "../components/AvailabilityBadge";
import { ProductImage } from "../components/ProductImage";
import { Empty, ErrorMessage, Loading } from "../components/StatusMessage";
import { useApi } from "../hooks/useApi";
import { useReload } from "../hooks/useReload";
import { currentLanguage } from "../i18n";
import { formatPrice, localized } from "../i18n/format";

function specValue(value: unknown, yes: string, no: string): string {
  if (typeof value === "boolean") return value ? yes : no;
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function specLabel(key: string): string {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function ProductPage() {
  const { t } = useTranslation();
  const lang = currentLanguage();
  const { id = "" } = useParams();
  const [key, reload] = useReload();
  const product = useApi((s) => catalogApi.product(id, s), [id, key]);

  if (product.status === "loading") return <Loading />;
  if (product.status === "error") {
    if (product.error.status === 404 || product.error.status === 422) {
      return (
        <>
          <Empty message={t("product.notFound")} />
          <Link to="/produits">{t("product.back")}</Link>
        </>
      );
    }
    return <ErrorMessage error={product.error} onRetry={reload} />;
  }

  const p = product.data;
  const name = localized(p, "name", lang);
  const description = localized(p, "description", lang);
  const image = p.images[0];

  return (
    <article className="product">
      <Link to="/produits" className="product__back">
        ← {t("product.back")}
      </Link>
      <div className="product__layout">
        <div className="product__media">
          <ProductImage
            src={image?.url}
            alt={image ? localized(image, "alt", lang) || name : ""}
            width={480}
            height={360}
          />
        </div>
        <div className="product__info">
          {p.brand && (
            <p className="card__brand">
              {t("product.brand")} : {p.brand}
            </p>
          )}
          <h1>{name}</h1>
          <p className="product__price">{formatPrice(p.price_cents, lang)}</p>
          <p className="card__sku">
            {t("product.sku")} {p.sku}
          </p>
          {description && <p>{description}</p>}

          <h2>{t("product.availability")}</h2>
          <ul className="availability">
            {p.availability.map((a) => (
              <li key={a.store_id}>
                <span>{a.store_name}</span> <AvailabilityBadge status={a.status} />
              </li>
            ))}
          </ul>
        </div>
      </div>

      {Object.keys(p.specs).length > 0 && (
        <section>
          <h2>{t("product.specs")}</h2>
          <table className="specs">
            <tbody>
              {Object.entries(p.specs).map(([k, v]) => (
                <tr key={k}>
                  <th scope="row">{specLabel(k)}</th>
                  <td>{specValue(v, t("product.yes"), t("product.no"))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </article>
  );
}
