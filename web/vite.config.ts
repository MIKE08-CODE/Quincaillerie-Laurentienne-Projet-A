/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// En développement, /api est relayé vers l'API FastAPI locale : le navigateur reste sur la même
// origine (pas de CORS ni de cookie tiers). En production, la même règle est faite par l'hébergeur.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target: env.VITE_API_PROXY_TARGET || "http://localhost:8000", changeOrigin: true },
      },
    },
    build: { sourcemap: false },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      restoreMocks: true,
    },
  };
});
