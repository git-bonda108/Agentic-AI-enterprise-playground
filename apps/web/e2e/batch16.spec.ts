import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 16 datasets, cost drill-down and console hours", () => {
  test("datasets show columns, downloads and trusted sources with loaders", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/data");
    await expect(page.getByRole("heading", { level: 1, name: "Datasets" })).toBeVisible();
    const sales = page.getByTestId("dataset-sales");
    await expect(sales.getByTestId("columns-sales")).toContainText("revenue");
    await expect(sales).toContainText("AdventureWorks");
    await expect(sales).toContainText('playground.frame("sales")');
    const [download] = await Promise.all([page.waitForEvent("download"), sales.getByRole("link", { name: "Download Monthly sales as CSV" }).click()]);
    expect(download.suggestedFilename()).toBe("sales.csv");
    await page.getByRole("tab", { name: /Trusted sources/ }).click();
    await expect(page.getByTestId("sources")).toContainText("Kaggle Datasets");
    await expect(page.getByTestId("sources")).toContainText("%pip install kagglehub");
    await expect(page.getByTestId("sources").getByRole("link", { name: "Open Hugging Face Datasets" })).toHaveAttribute("href", "https://huggingface.co/datasets");
  });

  test("cost cockpit drills from a layer into filtered rows and the ledger, and exports CSV", async ({ page }) => {
    await loginAs(page);
    const run = await page.request.post("/api/pg/v1/runs", { data: { blueprint_id: "knowledge-qa", input: { question: "What is the hotel limit per night?" }, wait: true } });
    expect(run.ok()).toBeTruthy();
    await page.goto("/operate/cost");
    await expect(page.getByTestId("cost-filters")).toContainText("No filters");
    await page.getByRole("tab", { name: "Blueprint" }).click();
    await expect(page.getByTestId("cost-table")).toContainText("Knowledge Q&A", { timeout: 10_000 });
    await page.getByTestId("cost-table").getByRole("button", { name: "Drill into Knowledge Q&A" }).click();
    await expect(page.getByTestId("cost-filters")).toContainText("Blueprint");
    await expect(page.getByTestId("cost-filters")).toContainText("Knowledge Q&A");
    await expect(page.getByRole("tab", { name: "Model", selected: true })).toBeVisible();
    await expect(page.getByTestId("ledger-table")).toContainText("Knowledge Q&A", { timeout: 10_000 });
    await expect(page.getByTestId("ledger-table")).toContainText("agent");
    await expect(page.getByText("Token split")).toBeVisible();
    const csv = await page.request.get("/api/pg/v1/usage/events?days=30&format=csv&blueprint_id=knowledge-qa");
    expect(csv.headers()["content-type"]).toContain("text/csv");
    expect(await csv.text()).toContain("Knowledge Q&A");
    await page.getByRole("button", { name: "Remove filter Blueprint Knowledge Q&A" }).click();
    await expect(page.getByTestId("cost-filters")).toContainText("No filters");
  });

  test("console shows hours tiles derived from ledger sessions", async ({ page }) => {
    await loginAs(page);
    await page.goto("/home");
    const tiles = page.getByTestId("hours-tiles");
    await expect(tiles.getByTestId("hours-chat")).toContainText("Chat hours");
    await expect(tiles.getByTestId("hours-agent")).toContainText("Agent hours");
    await expect(tiles.getByTestId("hours-notebook")).toContainText("Notebook hours");
    await expect(tiles.getByTestId("hours-total")).toContainText("All features");
    await expect(tiles.getByTestId("hours-agent")).toContainText(/min|h/);
  });
});
