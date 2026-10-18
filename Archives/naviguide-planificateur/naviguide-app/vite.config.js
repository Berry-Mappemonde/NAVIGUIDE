import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { visualizer } from "rollup-plugin-visualizer";

// Detect local development vs deployed environment
const isLocal = !process.env.VITE_DEPLOY_HOST;

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    tailwindcss(),
    mode === "analyze"
      && visualizer({
        filename: "dist/bundle-stats.html",
        gzipSize: true,
        open: false,
      }),
  ].filter(Boolean),
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/maplibre-gl")) return "maplibre";
          if (id.includes("node_modules/react-map-gl")) return "maplibre-react";
          if (id.includes("node_modules/lucide-react")) return "icons";
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: ["j19hah46.run.complete.dev", "all"],
    proxy: {
      "/proxy": { target: "http://localhost:8000", changeOrigin: true },
      // Exports Blue Intelligence — backend BI local (monorepo : backend/ sur :8001)
      "/bi": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/bi/, "/api"),
      },
    },
    // Local dev: use default HMR over localhost
    // Deployed: use WSS over production domain
    hmr: isLocal
      ? true
      : {
          protocol: "wss",
          host: "j19hah46.run.complete.dev",
          clientPort: 443,
        },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: ["j19hah46.run.complete.dev", "all"],
  },
}));
