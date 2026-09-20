import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const proxy = {
      "/route": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
        bypass(req) {
          // public/route.geojson = fallback interne, pas l'API searoute
          if (req.url?.startsWith("/route.geojson")) return req.url;
        },
      },
      "/proxy": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/ici": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/wind": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/wave": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/current": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/weather": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/api/v1": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/voyage": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/escale": { target: "http://127.0.0.1:8010", changeOrigin: true },
      "/logbook": { target: "http://127.0.0.1:8010", changeOrigin: true },
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
