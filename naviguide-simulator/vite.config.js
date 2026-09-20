import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// API_PROXY_TARGET=http://127.0.0.1:9 : simuler la CI (aucune API) en local.
const API = process.env.API_PROXY_TARGET || "http://127.0.0.1:8010";
const proxy = {
      "/route": {
        target: API,
        changeOrigin: true,
        bypass(req) {
          // public/route.geojson = fallback interne, pas l'API searoute
          if (req.url?.startsWith("/route.geojson")) return req.url;
        },
      },
      "/proxy": { target: API, changeOrigin: true },
      "/ici": { target: API, changeOrigin: true },
      "/wind": { target: API, changeOrigin: true },
      "/wave": { target: API, changeOrigin: true },
      "/current": { target: API, changeOrigin: true },
      "/weather": { target: API, changeOrigin: true },
      "/api/v1": { target: API, changeOrigin: true },
      "/voyage": { target: API, changeOrigin: true },
      "/escale": { target: API, changeOrigin: true },
      "/logbook": { target: API, changeOrigin: true },
      "/bi": {
        target: process.env.BI_PROXY_TARGET || "https://blueintelligence.online",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/bi/, "/api"),
      },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 5174,
    proxy,
  },
  // `vite preview` (build de prod) parle à la même API : le profil de prod
  // (lot J) et la fumée Playwright tournent sur une app complète.
  preview: {
    host: "0.0.0.0",
    port: 5174,
    proxy,
  },
});
