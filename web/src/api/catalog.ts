/** Types et appels du catalogue public (contrat d'API §7.2, §8.3). */

import { getJson } from "./client";

export type AvailabilityStatus = "in_stock" | "low_stock" | "out_of_stock";
export type ProductSort = "newest" | "price_asc" | "price_desc" | "name_asc" | "name_desc";
export type Lang = "fr" | "en";

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

export interface Store {
  id: string;
  name: string;
  address: string;
  phone: string | null;
  opening_hours: Record<string, [string, string]>;
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

export interface ProductImage {
  id: string;
  url: string;
  alt_fr: string | null;
  alt_en: string | null;
  position: number;
}

export interface StoreAvailability {
  store_id: string;
  store_name: string;
  status: AvailabilityStatus;
}

export interface ProductDetail extends ProductSummary {
  description_fr: string | null;
  description_en: string | null;
  specs: Record<string, unknown>;
  images: ProductImage[];
  availability: StoreAvailability[];
}

export interface ProductQuery {
  page?: number;
  size?: number;
  sort?: ProductSort;
  lang?: Lang;
  category_id?: string;
  brand_id?: string;
}

export const MAX_PAGE_SIZE = 50;

export const catalogApi = {
  categories: (signal?: AbortSignal) => getJson<CategoryNode[]>("/categories", {}, signal),
  stores: (signal?: AbortSignal) => getJson<Store[]>("/stores", {}, signal),
  products: (query: ProductQuery, signal?: AbortSignal) =>
    getJson<Page<ProductSummary>>("/products", { ...query }, signal),
  product: (id: string, signal?: AbortSignal) =>
    getJson<ProductDetail>(`/products/${encodeURIComponent(id)}`, {}, signal),
  search: (q: string, page: number, size: number, signal?: AbortSignal) =>
    getJson<Page<ProductSummary>>("/search", { q, page, size }, signal),
};
