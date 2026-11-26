import { Route, Routes } from "react-router-dom";

import { AuthProvider } from "../auth/AuthContext";
import { MainLayout } from "../layouts/MainLayout";
import { CatalogPage } from "../pages/CatalogPage";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ProductPage } from "../pages/ProductPage";
import { SearchPage } from "../pages/SearchPage";
import { PrivacyPage } from "../pages/PrivacyPage";
import { StoresPage } from "../pages/StoresPage";
import { AdminProductsPage } from "../pages/admin/AdminProductsPage";
import { MfaSetupPage } from "../pages/auth/MfaSetupPage";
import { AccountPage } from "../pages/auth/AccountPage";
import { LoginPage } from "../pages/auth/LoginPage";
import { ForgotPasswordPage, ResetPasswordPage } from "../pages/auth/PasswordPages";
import { RegisterPage } from "../pages/auth/RegisterPage";
import { VerifyEmailPage } from "../pages/auth/VerifyEmailPage";

export function AppRoutes() {
  return (
    <AuthProvider>
      <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="produits" element={<CatalogPage />} />
        <Route path="produits/:id" element={<ProductPage />} />
        <Route path="recherche" element={<SearchPage />} />
        <Route path="magasins" element={<StoresPage />} />
        <Route path="inscription" element={<RegisterPage />} />
        <Route path="connexion" element={<LoginPage />} />
        <Route path="verifier-courriel" element={<VerifyEmailPage />} />
        <Route path="mot-de-passe-oublie" element={<ForgotPasswordPage />} />
        <Route path="reinitialiser-mot-de-passe" element={<ResetPasswordPage />} />
        <Route path="compte" element={<AccountPage />} />
        <Route path="compte/mfa" element={<MfaSetupPage />} />
        <Route path="admin" element={<AdminProductsPage />} />
        <Route path="confidentialite" element={<PrivacyPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      </Routes>
    </AuthProvider>
  );
}
