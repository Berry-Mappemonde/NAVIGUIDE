import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const root = path.dirname(fileURLToPath(import.meta.url));

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
      // Climatologie BI : par le serveur local (server/bi_proxy.py, cache
      // disque, une requête par cellule par machine), jamais la prod en direct.
      // Incident 2026-09-21 : dev Vite + Playwright + agents → 600-800 req/s
      // sur blueintelligence.online. BI_PROXY_TARGET=https://blueintelligence.online
      // pour retrouver l'ancien direct (le chemin /bi devient alors /api).
      "/bi": process.env.BI_PROXY_TARGET
        ? {
          target: process.env.BI_PROXY_TARGET,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/bi/, "/api"),
        }
        : { target: API, changeOrigin: true },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(root, "index.html"),
        lotR8b: path.resolve(root, "lot-r8b.html"),
      },
    },
  },
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
    // Poste de recette vu depuis le cloud (Grok Bot) par un tunnel Cloudflare
    // (infra/agents/run_lots.py) : sans ceci, preview répond « Blocked request ».
    allowedHosts: [".trycloudflare.com", "localhost", "127.0.0.1"],
  },
});
