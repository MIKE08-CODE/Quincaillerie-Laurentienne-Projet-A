import { getJson } from "./client";

export interface Page<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}

export interface CategoryNode {
  id: string;
  slug: string;
  name_fr: string;
  name_en: string;
  children: CategoryNode[];
}

export interface ProductSummary {
  id: string;
  sku: string;
  name_fr: string;
  name_en: string;
  brand: string | null;
  price_cents: number;
  main_image_url: string | null;
  category_id: string | null;
}

export const PAGE_SIZE = 20;

export const catalogApi = {
  categories: () => getJson<CategoryNode[]>("/categories"),
  products: (page: number, categoryId?: string | null) =>
    getJson<Page<ProductSummary>>("/products", {
      page,
      size: PAGE_SIZE,
      sort: "name_asc",
      category_id: categoryId ?? undefined,
    }),
};
