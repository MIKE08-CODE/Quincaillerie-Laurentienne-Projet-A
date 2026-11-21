import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { ProductSummary } from "../api/catalog";
import { currentLanguage } from "../i18n";
import { formatPrice, localized } from "../i18n/format";

export function ProductCard({ product }: { product: ProductSummary }) {
  const { t } = useTranslation();
  const lang = currentLanguage();
  const name = localized(product, "name", lang);
  return (
    <li className="card">
      <Link to={`/produits/${product.id}`} className="card__link">
        <div className="card__image" aria-hidden={product.main_image_url ? undefined : true}>
          {product.main_image_url ? (
            <img src={product.main_image_url} alt="" loading="lazy" width={240} height={180} />
          ) : (
            <span>{t("product.noImage")}</span>
          )}
        </div>
        <div className="card__body">
          {product.brand && <p className="card__brand">{product.brand}</p>}
          <h3 className="card__title">{name}</h3>
          <p className="card__price">{formatPrice(product.price_cents, lang)}</p>
          <p className="card__sku">
            {t("product.sku")} {product.sku}
          </p>
        </div>
      </Link>
    </li>
  );
}

export function ProductGrid({ products }: { products: ProductSummary[] }) {
  return (
    <ul className="grid" aria-live="polite">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} />
      ))}
    </ul>
  );
}
