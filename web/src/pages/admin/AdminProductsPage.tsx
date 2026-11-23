import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { type AdminPage, type AdminProduct, adminApi } from "../../api/admin";
import { ApiError } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { Loading } from "../../components/StatusMessage";
import { formatPrice } from "../../i18n/format";
import { currentLanguage } from "../../i18n";

const ADMIN_ERRORS = new Set([
  "image_storage_not_configured",
  "image_storage_unavailable",
  "image_too_large",
  "unsupported_image_type",
  "image_type_mismatch",
  "image_dimensions_too_large",
  "image_empty",
  "image_invalid",
  "mfa_required",
  "insufficient_role",
  "not_authenticated",
  "invalid_token",
]);

function AdminError({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  const code = error instanceof ApiError ? error.code : "unknown";
  return (
    <p className="status status--error" role="alert">
      {t(ADMIN_ERRORS.has(code) ? `admin.errors.${code}` : "admin.errors.generic")}
    </p>
  );
}

/** Édition d'un produit : noms, prix, activation, images (A-ADM-01). */
function ProductEditor({ product, token, onSaved }: { product: AdminProduct; token: string; onSaved: () => void }) {
  const { t } = useTranslation();
  const [nameFr, setNameFr] = useState(product.name_fr);
  const [nameEn, setNameEn] = useState(product.name_en);
  const [price, setPrice] = useState((product.price_cents / 100).toFixed(2));
  const [active, setActive] = useState(product.is_active);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(done);
      onSaved();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function save(event: FormEvent) {
    event.preventDefault();
    const cents = Math.round(Number(price.replace(",", ".")) * 100);
    if (!Number.isFinite(cents) || cents < 0) {
      setError(new ApiError(422, "invalid_price", "Prix invalide"));
      return;
    }
    void run(
      () => adminApi.update(token, product.id, { name_fr: nameFr, name_en: nameEn, price_cents: cents, is_active: active }),
      t("admin.saved"),
    );
  }

  function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    void run(() => adminApi.uploadImage(token, product.id, file, { alt_fr: nameFr, alt_en: nameEn }), t("admin.uploaded"));
  }

  return (
    <div className="admin__editor">
      <form className="form" onSubmit={save} aria-label={t("admin.editLabel", { sku: product.sku })}>
        <label className="field">
          <span>{t("admin.fields.nameFr")}</span>
          <input required maxLength={200} value={nameFr} onChange={(e) => setNameFr(e.target.value)} />
        </label>
        <label className="field">
          <span>{t("admin.fields.nameEn")}</span>
          <input required maxLength={200} value={nameEn} onChange={(e) => setNameEn(e.target.value)} />
        </label>
        <label className="field">
          <span>{t("admin.fields.price")}</span>
          <input inputMode="decimal" required value={price} onChange={(e) => setPrice(e.target.value)} />
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          <span>{t("admin.fields.active")}</span>
        </label>
        <button type="submit" className="button" disabled={busy}>
          {t("admin.save")}
        </button>
      </form>
      <form className="form" onSubmit={upload}>
        <label className="field">
          <span>{t("admin.fields.image")}</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <p className="field__hint">{t("admin.imageHint")}</p>
        <button type="submit" className="button" disabled={busy || !file}>
          {t("admin.upload")}
        </button>
      </form>
      {product.images.length > 0 && (
        <ul className="admin__images">
          {product.images.map((image) => (
            <li key={image.id}>
              <a href={image.url} target="_blank" rel="noreferrer">
                {t("admin.imageN", { n: image.position + 1 })}
              </a>{" "}
              <button
                type="button"
                className="button button--ghost"
                disabled={busy}
                onClick={() => void run(() => adminApi.deleteImage(token, product.id, image.id), t("admin.deleted"))}
              >
                {t("admin.deleteImage")}
              </button>
            </li>
          ))}
        </ul>
      )}
      {message && <p role="status">{message}</p>}
      <AdminError error={error} />
    </div>
  );
}

/** Tableau d'administration minimal du catalogue (A-ADM-01), réservé à l'administrateur avec MFA. */
export function AdminProductsPage() {
  const { t } = useTranslation();
  const { token, user, restore } = useAuth();
  const [checking, setChecking] = useState(!user);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState<string | null>(null);
  const tried = useRef(false);
  const lang = currentLanguage();

  useEffect(() => {
    if (user || tried.current) return;
    tried.current = true;
    void restore().finally(() => setChecking(false));
  }, [user, restore]);

  const load = useCallback(() => {
    if (!token || user?.role !== "admin") return;
    adminApi
      .products(token, page)
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch(setError);
  }, [token, user, page]);

  useEffect(load, [load]);

  if (checking) return <Loading />;
  if (!user || !token) {
    return (
      <section>
        <h1>{t("admin.title")}</h1>
        <p>
          {t("admin.signIn")} <Link to="/connexion">{t("auth.login.title")}</Link>
        </p>
      </section>
    );
  }
  if (user.role !== "admin") {
    return (
      <section>
        <h1>{t("admin.title")}</h1>
        <p role="alert">{t("admin.errors.insufficient_role")}</p>
      </section>
    );
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  return (
    <section className="admin">
      <h1>{t("admin.title")}</h1>
      <AdminError error={error} />
      {!data && !error && <Loading />}
      {data && (
        <>
          <p>{t("admin.count", { total: data.total })}</p>
          <table className="admin__table">
            <thead>
              <tr>
                <th scope="col">{t("admin.columns.sku")}</th>
                <th scope="col">{t("admin.columns.name")}</th>
                <th scope="col">{t("admin.columns.price")}</th>
                <th scope="col">{t("admin.columns.status")}</th>
                <th scope="col">
                  <span className="visually-hidden">{t("admin.columns.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((product) => (
                <tr key={product.id}>
                  <td>{product.sku}</td>
                  <td>
                    {lang === "en" ? product.name_en : product.name_fr}
                    {open === product.id && (
                      <ProductEditor product={product} token={token} onSaved={load} />
                    )}
                  </td>
                  <td>{formatPrice(product.price_cents, lang)}</td>
                  <td>{product.is_active ? t("admin.active") : t("admin.inactive")}</td>
                  <td>
                    <button
                      type="button"
                      className="button button--ghost"
                      aria-expanded={open === product.id}
                      onClick={() => setOpen(open === product.id ? null : product.id)}
                    >
                      {open === product.id ? t("admin.close") : t("admin.edit", { sku: product.sku })}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <nav className="pagination" aria-label={t("pagination.label")}>
            <button type="button" className="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              {t("pagination.previous")}
            </button>
            <span>{t("pagination.page", { page, pages })}</span>
            <button type="button" className="button" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              {t("pagination.next")}
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
