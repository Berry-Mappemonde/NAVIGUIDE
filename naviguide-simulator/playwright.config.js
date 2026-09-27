// Fumée Playwright (lot H) sur le build de prod servi par `vite preview`.
// Sans API : l'app doit tenir debout seule (repli route interne, briefing
// « les couches n'ont pas répondu »). Une seule fois par PR, chromium seul.
// Port : 5174 par défaut ; `PW_PORT=5199 npm run e2e` quand 5174 est déjà pris
// (serveur de dev du dépôt principal pendant qu'un agent travaille dans un worktree).
// Lot RF11 : `PW_WITH_API=1` démarre aussi l'API hors ligne (stock figé).
import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_PORT || 5174);
const origin = `http://127.0.0.1:${port}`;
const withApi = process.env.PW_WITH_API === "1";
// Worktree : :8010 est souvent déjà pris par le dépôt principal.
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
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  // Le job GitHub a 15 min (install + fumée + lots). Les lots sont
  // informatifs : deux workers et un plafond pour finir avant que le
  // job n'annule une fumée déjà verte. Avec stock figé : 4 workers, 20 min.
  workers: process.env.CI ? (withApi ? 4 : 2) : undefined,
  globalTimeout: process.env.CI
    ? (withApi ? 20 * 60 * 1000 : 8 * 60 * 1000)
    : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: origin,
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
  },
  webServer: withApi ? [viteServer, apiServer] : [viteServer],
});
