// Fumée Playwright (lot H) sur le build de prod servi par `vite preview`.
// Sans API : l'app doit tenir debout seule (repli route interne, briefing
// « les couches n'ont pas répondu »). Une seule fois par PR, chromium seul.
import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_PORT || 5174);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
