import { useTranslation } from "react-i18next";

import type { CategoryNode } from "../api/catalog";
import { currentLanguage } from "../i18n";
import { localized } from "../i18n/format";

export function CategoryTree({
  nodes,
  selected,
  onSelect,
}: {
  nodes: CategoryNode[];
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const { t } = useTranslation();
  return (
    <nav className="categories" aria-label={t("catalog.categories")}>
      <button
        type="button"
        className={`categories__item${selected === null ? " is-active" : ""}`}
        aria-current={selected === null ? "true" : undefined}
        onClick={() => onSelect(null)}
      >
        {t("catalog.allCategories")}
      </button>
      <Branch nodes={nodes} selected={selected} onSelect={onSelect} />
    </nav>
  );
}

function Branch({
  nodes,
  selected,
  onSelect,
}: {
  nodes: CategoryNode[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const lang = currentLanguage();
  return (
    <ul>
      {nodes.map((node) => (
        <li key={node.id}>
          <button
            type="button"
            className={`categories__item${selected === node.id ? " is-active" : ""}`}
            aria-current={selected === node.id ? "true" : undefined}
            onClick={() => onSelect(node.id)}
          >
            {localized(node, "name", lang)}
          </button>
          {node.children.length > 0 && <Branch nodes={node.children} selected={selected} onSelect={onSelect} />}
        </li>
      ))}
    </ul>
  );
}
