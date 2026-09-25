import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { loginAs } from "./helpers";

const SERIOUS = ["serious", "critical"];

test.describe("Accessibility", () => {
  test("login page has no serious violations", async ({ page }) => {
    await page.goto("/login");
    await page.waitForTimeout(1500);
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations.filter((v) => SERIOUS.includes(v.impact ?? ""));
    expect(bad, JSON.stringify(bad, null, 2)).toEqual([]);
  });

  test("console home has no serious violations", async ({ page }) => {
    await loginAs(page);
    await page.waitForTimeout(1500);
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations.filter((v) => SERIOUS.includes(v.impact ?? ""));
    expect(bad, JSON.stringify(bad, null, 2)).toEqual([]);
  });
});
