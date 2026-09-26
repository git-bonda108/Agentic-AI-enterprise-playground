import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 7 evals and canary", () => {
  test("built-in golden set runs, shows per-case checks and the hardening ladder", async ({ page }) => {
    await loginAs(page);
    await page.goto("/evaluate/evals");
    await expect(page.getByRole("heading", { level: 1, name: "Evals" })).toBeVisible();
    await page.getByRole("button", { name: "Open suite Knowledge Q&A golden set" }).click();
    await expect(page.getByTestId("hardening-ladder")).toBeVisible();
    await page.getByRole("button", { name: "Run suite" }).click();
    await expect(page.getByTestId("gate-verdict")).toContainText("Gate cleared", { timeout: 90_000 });
    await expect(page.getByTestId("case-results").locator("li")).toHaveCount(10);
    await expect(page.getByTestId("case-results")).toContainText("Correctness:");
    await expect(page.getByTestId("hardening-ladder")).toContainText("Gated");
  });

  test("guided builder creates a suite from a sample with a rubric, gate and canary, then the canary board runs it", async ({ page }) => {
    await loginAs(page);
    await page.goto("/evaluate/evals");
    await page.getByRole("button", { name: "Build a suite" }).click();
    await page.getByLabel("Agent under test").selectOption("knowledge-qa");
    const suiteName = `Policy answers ${Date.now().toString(36)}`;
    await page.getByLabel("Suite name").fill(suiteName);
    await page.getByRole("button", { name: "Next step" }).click();
    await page.getByRole("button", { name: "Add sample Hotel limit" }).click();
    await page.getByLabel("Case input").fill("What do I need for a purchase over 50,000 USD?");
    await page.getByLabel("Answer must contain").fill("POL-002");
    await page.getByRole("button", { name: "Add written case" }).click();
    await expect(page.getByTestId("builder-cases").locator("li")).toHaveCount(2);
    await page.getByRole("button", { name: "Next step" }).click();
    await page.getByLabel("Criterion Groundedness").check();
    await page.getByRole("button", { name: "Next step" }).click();
    await page.getByLabel("Minimum pass rate").fill("100");
    await page.getByRole("button", { name: "Next step" }).click();
    await page.getByLabel("Enable nightly canary").check();
    await page.getByRole("button", { name: "Create suite" }).click();
    await expect(page.getByTestId("suite-detail")).toContainText(suiteName, { timeout: 10_000 });
    await expect(page.getByTestId("suite-detail")).toContainText("Correctness, Groundedness");
    await page.getByRole("button", { name: "Run suite" }).click();
    await expect(page.getByTestId("gate-verdict")).toContainText("Gate cleared", { timeout: 60_000 });
    await page.goto("/evaluate/canary");
    await expect(page.getByTestId("canary-table")).toContainText(suiteName);
    await page.getByRole("button", { name: `Run canary now for ${suiteName}` }).click();
    await expect(page.getByTestId("canary-table")).toContainText("stable", { timeout: 60_000 });
    await expect(page.getByTestId("drift-chart")).toBeVisible();
  });
});
