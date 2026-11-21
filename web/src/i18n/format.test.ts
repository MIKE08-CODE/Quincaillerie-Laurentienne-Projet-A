import { describe, expect, it } from "vitest";

import { formatPrice, localized } from "./format";

describe("formatPrice", () => {
  it("formate les cents en dollars canadiens selon la langue", () => {
    expect(formatPrice(12999, "fr").replace(/\s/g, " ")).toBe("129,99 $");
    expect(formatPrice(12999, "en")).toBe("$129.99");
    expect(formatPrice(0, "en")).toBe("$0.00");
  });
});

describe("localized", () => {
  it("choisit le champ de la langue et retombe sur le français", () => {
    const item = { name_fr: "Perceuse", name_en: "Drill", description_fr: "Texte" };
    expect(localized(item, "name", "en")).toBe("Drill");
    expect(localized(item, "name", "fr")).toBe("Perceuse");
    expect(localized(item, "description", "en")).toBe("Texte");
    expect(localized(item, "absent", "fr")).toBe("");
  });
});
