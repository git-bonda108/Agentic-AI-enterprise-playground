import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 11 runnable notebooks", () => {
  test("gallery lists Gen AI and Agentic AI notebooks with levels, and filters by level", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/notebooks");
    await expect(page.getByRole("heading", { level: 1, name: "Notebooks" })).toBeVisible();
    const gallery = page.getByTestId("notebook-gallery");
    await expect(gallery.getByRole("article")).toHaveCount(12);
    await expect(page.getByRole("region", { name: "Gen AI notebooks" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Agentic AI notebooks" })).toBeVisible();
    await expect(page.getByTestId("gallery-hello-playground")).toContainText("Starter");
    await expect(page.getByTestId("gallery-doc-reconciliation")).toContainText("Advanced");
    await page.getByRole("button", { name: "Starter", exact: true }).click();
    await expect(gallery.getByRole("article")).toHaveCount(4);
  });

  test("a notebook runs end to end in the sandbox from the gallery", async ({ page }) => {
    test.setTimeout(180_000);
    await loginAs(page);
    await page.goto("/build/notebooks");
    await page.getByTestId("gallery-hello-playground").getByRole("link", { name: "Run in sandbox" }).click();
    await expect(page).toHaveURL(/run=sandbox/);
    await expect(page.getByTestId("notebook-exec-summary")).toContainText("code cells ran", { timeout: 120_000 });
    await expect(page.getByTestId("cell-output-0")).toContainText("playground 1.1.0 · sandbox");
    await expect(page.getByTestId("cell-output-2")).toContainText(/\S/);
    await page.getByLabel("Sandbox code").fill("import playground as pg\nprint(len(pg.models()) > 0)");
    await page.getByRole("button", { name: "Run in sandbox" }).click();
    await expect(page.getByTestId("sandbox-output")).toContainText("True", { timeout: 30_000 });
  });

  test("a blueprint notebook explains its next steps and offers external compute", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/notebooks?blueprint=sage-lens");
    await page.getByRole("tab", { name: "Server sandbox" }).click();
    await expect(page.getByTestId("notebook-cells")).toContainText("Run the MVP");
    await expect(page.getByTestId("notebook-cells")).toContainText("Reference implementations");
    await page.getByRole("button", { name: "More compute" }).click();
    const panel = page.getByTestId("compute-panel");
    await expect(panel).toContainText("NVIDIA Brev");
    await expect(panel).toContainText("Google Colab");
    await expect(panel.getByRole("link", { name: /Open NVIDIA Brev/ })).toHaveAttribute("href", /brev\.nvidia\.com/);
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download notebook" }).click();
    expect((await download).suggestedFilename()).toBe("sage-lens.ipynb");
  });
});
