import { useTranslation } from "react-i18next";

export function Pagination({
  page,
  size,
  total,
  onChange,
}: {
  page: number;
  size: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const { t } = useTranslation();
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label={t("pagination.label")}>
      <button type="button" className="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        {t("pagination.previous")}
      </button>
      <span>{t("pagination.page", { page, pages })}</span>
      <button type="button" className="button" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        {t("pagination.next")}
      </button>
    </nav>
  );
}
