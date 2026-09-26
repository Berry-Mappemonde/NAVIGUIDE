// Fumée Playwright (lot H) sur le build de prod servi par `vite preview`.
// Sans API : l'app doit tenir debout seule (repli route interne, briefing
// « les couches n'ont pas répondu »). Une seule fois par PR, chromium seul.
// Port : 5174 par défaut ; `PW_PORT=5199 npm run e2e` quand 5174 est déjà pris
// (serveur de dev du dépôt principal pendant qu'un agent travaille dans un worktree).
import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_PORT || 5174);
const origin = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  // Le job GitHub a 15 min (install + fumée + lots). Les lots sont
  // informatifs : deux workers et un plafond pour finir avant que le
  // job n'annule une fumée déjà verte.
  workers: process.env.CI ? 2 : undefined,
  globalTimeout: process.env.CI ? 8 * 60 * 1000 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: origin,
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
    url: origin,
    // Sur un port dédié (PW_PORT), on veut toujours SON serveur, jamais celui d'un autre checkout.
    reuseExistingServer: !process.env.CI && !process.env.PW_PORT,
    timeout: 60_000,
  },
});
