import type { Language } from "./index";

/** Prix en cents (entier, jamais de virgule flottante côté API) → texte localisé en dollars canadiens. */
export function formatPrice(cents: number, lang: Language): string {
  return new Intl.NumberFormat(lang === "en" ? "en-CA" : "fr-CA", { style: "currency", currency: "CAD" }).format(
    cents / 100,
  );
}

/** Choisit le champ bilingue `<champ>_fr` ou `<champ>_en`, avec repli sur le français. */
export function localized<T extends object>(item: T, field: string, lang: Language): string {
  const record = item as Record<string, unknown>;
  const value = record[`${field}_${lang}`] ?? record[`${field}_fr`];
  return typeof value === "string" ? value : "";
}
