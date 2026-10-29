import { expect, test } from "@playwright/test";
import { dismissNotForNav } from "../helpers.js";
const IDS = ["welcome","models","live","briefing","layers","replay","trace","return"];
test("shots", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/"); await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("demo-walkthrough-launch").click();
  const dir = process.env.SHOTS;
  for (let i = 0; i < IDS.length; i++) {
    await expect(page.getByTestId("demo-walkthrough-panel")).toHaveAttribute("data-step", IDS[i]);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${dir}/${String(i+1).padStart(2,"0")}-${IDS[i]}.png` });
    if (i < IDS.length - 1) await page.getByTestId("demo-walkthrough-next").click();
  }
});
