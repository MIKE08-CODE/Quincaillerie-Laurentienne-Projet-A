import { Route, Routes } from "react-router-dom";

import { MainLayout } from "../layouts/MainLayout";
import { CatalogPage } from "../pages/CatalogPage";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ProductPage } from "../pages/ProductPage";
import { SearchPage } from "../pages/SearchPage";
import { StoresPage } from "../pages/StoresPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="produits" element={<CatalogPage />} />
        <Route path="produits/:id" element={<ProductPage />} />
        <Route path="recherche" element={<SearchPage />} />
        <Route path="magasins" element={<StoresPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
