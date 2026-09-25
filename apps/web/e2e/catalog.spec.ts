import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 4 catalog", () => {
  test("blueprints page lists families, filters and opens a detail", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/blueprints");
    await expect(page.getByRole("heading", { level: 1, name: "Blueprints" })).toBeVisible();
    const green = await page.getByTestId("green-count").textContent();
    expect(Number(green?.split(" ")[0])).toBeGreaterThanOrEqual(60);
    await page.getByRole("tab", { name: /^Role/ }).click();
    await expect(page.getByTestId("catalog-grid").getByRole("article").first()).toBeVisible();
    const roleCount = await page.getByTestId("catalog-grid").getByRole("article").count();
    expect(roleCount).toBeGreaterThanOrEqual(60);
    await page.getByLabel("Search blueprints").fill("security");
    await expect(page.getByTestId("catalog-grid")).toContainText("Security Reviewer", { timeout: 10_000 });
    await page.getByRole("button", { name: "Security Reviewer" }).click();
    await expect(page.getByTestId("entry-instructions")).toContainText(/security/i);
    await page.keyboard.press("Escape");
    await page.getByLabel("Search blueprints").fill("");
    await page.getByRole("tab", { name: /^Cloud/ }).click();
    await expect(page.getByTestId("catalog-grid")).toContainText("AgentCore");
    await expect(page.getByRole("link", { name: /Deploy: Provider runtime guide/ }).first()).toBeVisible();
  });

  test("an imported role agent runs through the generic runner", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/blueprints");
    await page.getByLabel("Search blueprints").fill("code reviewer");
    await expect(page.getByTestId("catalog-grid")).toContainText("Code Reviewer", { timeout: 10_000 });
    await page.getByTestId("catalog-grid").getByRole("article", { name: "Code Reviewer" }).getByRole("button", { name: /^Run:/ }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page).toHaveURL(/\/operate\/runs\//);
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Code Reviewer" })).toBeVisible();
    await expect(page.getByTestId("run-steps")).toContainText("Code Reviewer responded");
    await expect(page.getByTestId("run-output")).toContainText(/fake|review/i);
  });

  test("a low-code template answers from knowledge", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/blueprints");
    await page.getByRole("tab", { name: /^Low-code/ }).click();
    await page.getByTestId("catalog-grid").getByRole("article", { name: "My company policy" }).getByRole("button", { name: /^Run:/ }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 20_000 });
    await expect(page.getByTestId("run-steps")).toContainText("retrieved");
    await expect(page.getByTestId("run-output")).toContainText("POL-");
  });
});
