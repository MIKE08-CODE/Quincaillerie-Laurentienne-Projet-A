/** Textes FR/EN de l'application (langue de l'appareil, français par défaut). */
export type Language = "fr" | "en";

const texts = {
  fr: {
    title: "Catalogue",
    all: "Tout",
    loading: "Chargement des produits…",
    error: "Impossible de charger le catalogue.",
    network_error: "Impossible de joindre le serveur. Vérifiez votre connexion.",
    retry: "Réessayer",
    empty: "Aucun produit dans cette catégorie.",
    count: (n: number) => (n > 1 ? `${n} produits` : `${n} produit`),
    more: "Charger plus",
  },
  en: {
    title: "Catalogue",
    all: "All",
    loading: "Loading products…",
    error: "Unable to load the catalogue.",
    network_error: "Cannot reach the server. Check your connection.",
    retry: "Try again",
    empty: "No products in this category.",
    count: (n: number) => (n === 1 ? "1 product" : `${n} products`),
    more: "Load more",
  },
} as const;

export type Texts = (typeof texts)[Language];

export function deviceLanguage(): Language {
  try {
    return Intl.DateTimeFormat().resolvedOptions().locale.toLowerCase().startsWith("en") ? "en" : "fr";
  } catch {
    return "fr";
  }
}

export function getTexts(lang: Language): Texts {
  return texts[lang];
}

export function formatPrice(cents: number, lang: Language): string {
  return new Intl.NumberFormat(lang === "en" ? "en-CA" : "fr-CA", { style: "currency", currency: "CAD" }).format(
    cents / 100,
  );
}
