import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en/common.json";
import fr from "./locales/fr/common.json";

export const LANGUAGES = ["fr", "en"] as const;
export type Language = (typeof LANGUAGES)[number];
const STORAGE_KEY = "ql.language";

function initialLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "fr" || saved === "en") return saved;
  } catch {
    // stockage indisponible (navigation privée) : français par défaut
  }
  return "fr"; // ENF-10 : français par défaut
}

void i18n.use(initReactI18next).init({
  resources: { fr: { common: fr }, en: { common: en } },
  lng: initialLanguage(),
  fallbackLng: "fr",
  defaultNS: "common",
  interpolation: { escapeValue: false }, // React échappe déjà le texte
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  try {
    window.localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    // préférence non mémorisée : sans conséquence
  }
});

export function currentLanguage(): Language {
  return i18n.language === "en" ? "en" : "fr";
}

export default i18n;
