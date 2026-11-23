/** Administration du catalogue (A-ADM-01) : routes /api/v1/admin/*, administrateur avec MFA. */
import { getJsonAuth, sendFile, sendJson } from "./client";

export interface AdminImage {
  id: string;
  url: string;
  alt_fr: string | null;
  alt_en: string | null;
  position: number;
}

export interface AdminProduct {
  id: string;
  sku: string;
  name_fr: string;
  name_en: string;
  price_cents: number;
  is_active: boolean;
  images: AdminImage[];
}

export interface AdminPage {
  items: AdminProduct[];
  page: number;
  size: number;
  total: number;
}

export type ProductPatch = Partial<Pick<AdminProduct, "name_fr" | "name_en" | "price_cents" | "is_active">>;

export const adminApi = {
  products: (token: string, page: number) => getJsonAuth<AdminPage>("/admin/products", token, { page, size: 20 }),
  update: (token: string, id: string, patch: ProductPatch) =>
    sendJson<AdminProduct>(`/admin/products/${id}`, patch, { method: "PATCH", token }),
  uploadImage: (token: string, id: string, file: File, alt: { alt_fr?: string; alt_en?: string }) =>
    sendFile<AdminImage>(`/admin/products/${id}/images/upload`, file, token, alt),
  deleteImage: (token: string, id: string, imageId: string) =>
    sendJson<void>(`/admin/products/${id}/images/${imageId}`, undefined, { method: "DELETE", token }),
  mfaSetup: (token: string) => sendJson<{ secret: string; otpauth_uri: string }>("/auth/mfa/setup", undefined, { token }),
  mfaEnable: (token: string, code: string) =>
    sendJson<{ access_token: string; expires_in: number }>("/auth/mfa/enable", { code }, { token }),
};
