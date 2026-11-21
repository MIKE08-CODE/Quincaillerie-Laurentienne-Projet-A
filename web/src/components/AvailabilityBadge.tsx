import { useTranslation } from "react-i18next";

import type { AvailabilityStatus } from "../api/catalog";

export function AvailabilityBadge({ status }: { status: AvailabilityStatus }) {
  const { t } = useTranslation();
  return <span className={`badge badge--${status}`}>{t(`status.${status}`)}</span>;
}
