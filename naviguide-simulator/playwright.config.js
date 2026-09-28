// Recette automatique (lot RG16 / D11) : fumée + specs de lots.
// Port : 5174 par défaut ; `PW_PORT=5199 npm run e2e` quand 5174 est déjà pris.
// `PW_WITH_API=1` démarre l'API hors ligne (stock figé, lot RF11).
import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_PORT || 5174);
const origin = `http://127.0.0.1:${port}`;
const withApi = process.env.PW_WITH_API === "1";
const apiPort = Number(
  process.env.PW_API_PORT || process.env.NAVIGUIDE_API_PORT || (process.env.PW_PORT ? 8019 : 8010),
);
const apiOrigin = `http://127.0.0.1:${apiPort}`;

const viteServer = {
  command: `npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
  url: origin,
  reuseExistingServer: !process.env.CI && !process.env.PW_PORT,
  timeout: 60_000,
  env: withApi
    ? { ...process.env, API_PROXY_TARGET: apiOrigin }
    : process.env,
};

const apiServer = {
  command: "bash scripts/e2e-store-api.sh",
  url: apiOrigin,
  reuseExistingServer: false,
  timeout: 180_000,
  env: {
    ...process.env,
    NAVIGUIDE_OFFLINE: "1",
    NAVIGUIDE_API_PORT: String(apiPort),
    NAVIGUIDE_OFFICIAL_WORKER: "0",
  },
};

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  workers: 4,
  globalTimeout: 12 * 60 * 1000,
  reporter: process.env.CI
    ? [
      ["github"],
      ["list"],
      ["json", { outputFile: "test-results/e2e.json" }],
      ["html", { open: "never" }],
    ]
    : "list",
  use: {
    baseURL: origin,
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: process.env.CI ? "off" : "retain-on-failure",
    navigationTimeout: 20_000,
  },
  webServer: withApi ? [viteServer, apiServer] : [viteServer],
});
