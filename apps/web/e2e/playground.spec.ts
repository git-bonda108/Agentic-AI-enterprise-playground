import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 1 playground", () => {
  test("chat streams a reply, meters it, and saves the conversation", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/playground");
    await expect(page.getByRole("heading", { level: 1, name: "Playground" })).toBeVisible();

    const marker = `ledger-${Date.now()}`;
    await page.getByLabel("Prompt", { exact: true }).fill(`Hello ${marker}`);
    await page.keyboard.press("Enter");

    await expect(page.getByText(/Fake reply from/)).toBeVisible({ timeout: 15_000 });
    const usage = page.getByTestId("usage-chip").first();
    await expect(usage).toContainText("$");
    await expect(usage).toContainText("in ·");

    // Conversation appears in the list with the prompt as title
    await expect(page.getByRole("button", { name: new RegExp(`Hello ${marker}`) })).toBeVisible();

    // Search narrows the list to it
    await page.getByLabel("Search conversations").fill(marker);
    await expect(page.getByRole("button", { name: new RegExp(`Hello ${marker}`) })).toBeVisible();
    await expect(page.locator('aside[aria-label="Conversations"] li')).toHaveCount(1);

    // Follow-up keeps the same conversation and adds a second metered reply
    await page.getByLabel("Prompt", { exact: true }).fill("And a follow-up");
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("usage-chip")).toHaveCount(2, { timeout: 15_000 });
  });

  test("view code shows the request in five languages", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/playground");
    await page.getByLabel("Prompt", { exact: true }).fill("Explain caching");
    await page.getByRole("button", { name: "View code" }).click();
    await expect(page.getByTestId("snippet-python")).toContainText("client.chat.completions.create");
    await expect(page.getByTestId("snippet-python")).toContainText("Explain caching");
    await page.getByRole("tab", { name: "curl" }).click();
    await expect(page.getByTestId("snippet-curl")).toContainText("curl ");
    await page.getByRole("tab", { name: "Java" }).click();
    await expect(page.getByTestId("snippet-java")).toContainText("OpenAIOkHttpClient");
  });

  test("compare runs the prompt on several models at once", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/playground");
    await page.getByRole("tab", { name: "Compare" }).click();
    await page.getByLabel("Compare GPT-5.6 Terra", { exact: true }).check();
    await page.getByLabel("Compare DeepSeek V4 Flash", { exact: true }).check();
    await page.getByLabel("Prompt", { exact: true }).fill("compare me");
    await page.getByRole("button", { name: "Send message" }).click();
    await expect(page.getByText(/Fake reply from/)).toHaveCount(3, { timeout: 20_000 });
    await expect(page.getByTestId("compare-grid")).toContainText("GPT-5.6 Terra");
    await expect(page.getByTestId("compare-grid")).toContainText("DeepSeek V4 Flash");
  });

  test("console home shows live ledger numbers", async ({ page }) => {
    await loginAs(page);
    await expect(page.getByText(/live · (org|you)/).first()).toBeVisible();
    await expect(page.getByText("Spend this month")).toBeVisible();
  });
});
