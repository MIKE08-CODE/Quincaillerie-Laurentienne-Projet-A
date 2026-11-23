import { useTranslation } from "react-i18next";

/**
 * Politique de confidentialité — ÉBAUCHE « À valider » (Loi 25). Le texte décrit les traitements
 * réellement effectués par l'application ; il n'est pas définitif tant qu'il n'a pas été approuvé par
 * le responsable du projet. Les éléments que le code ne peut pas établir sont marqués « À compléter ».
 */
export function PrivacyPage() {
  const { t } = useTranslation();
  const sections = ["controller", "data", "purposes", "hosting", "retention", "rights", "contact"] as const;
  return (
    <article className="privacy">
      <p className="status status--error" role="note">
        {t("privacy.draft")}
      </p>
      <h1>{t("privacy.title")}</h1>
      <p>{t("privacy.version")}</p>
      {sections.map((key) => (
        <section key={key}>
          <h2>{t(`privacy.${key}.title`)}</h2>
          <p>{t(`privacy.${key}.body`)}</p>
        </section>
      ))}
    </article>
  );
}
