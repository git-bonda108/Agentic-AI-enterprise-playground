import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 10 provider keys and models", () => {
  test("keys drawer: add, test and remove a personal NVIDIA NIM key", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/models");
    await page.getByTestId("keys-chip").click();
    await expect(page.getByTestId("keys-drawer")).toBeVisible();
    await expect(page.getByTestId("keys-drawer")).toContainText("Provider keys");
    const row = page.getByTestId("key-row-nvidia-nim");
    await expect(row).toContainText("Get a key");
    await row.getByRole("button", { name: "Add key" }).click();
    await row.getByLabel("NVIDIA NIM API key").fill("nvapi-e2e-personal-key-ABCD");
    await row.getByRole("button", { name: "Save key" }).click();
    await expect(row.getByTestId("key-status-nvidia-nim")).toContainText("••••ABCD", { timeout: 10_000 });
    await expect(page.getByTestId("keys-drawer")).not.toContainText("nvapi-e2e-personal-key");
    await row.getByRole("button", { name: "Test key" }).click();
    await expect(row.getByTestId("key-test-result")).toContainText("Works", { timeout: 15_000 });
    await row.getByRole("button", { name: "Remove key" }).click();
    await expect(row.getByTestId("key-status-nvidia-nim")).not.toContainText("••••ABCD", { timeout: 10_000 });
  });

  test("keys drawer rejects a key with the wrong prefix", async ({ page }) => {
    await loginAs(page);
    await page.goto("/home");
    await page.getByTestId("keys-chip").click();
    const row = page.getByTestId("key-row-anthropic");
    await row.getByRole("button", { name: "Add key" }).click();
    await row.getByLabel("Anthropic API key").fill("sk-wrong-prefix-key");
    await row.getByRole("button", { name: "Save key" }).click();
    await expect(row).toContainText("start with sk-ant-");
  });

  test("model catalog lists the NVIDIA, Mistral, xAI, Groq and Cohere models with documentation", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/models");
    await expect(page.getByRole("heading", { level: 1, name: "Models" })).toBeVisible();
    for (const name of ["Nemotron 3 Super 120B", "Hermes 4 405B", "Mistral Medium 3.5", "Grok 4.7", "GPT-OSS 120B", "Command A"]) {
      await expect(page.getByText(name, { exact: false }).first()).toBeVisible();
    }
    await expect(page.getByRole("link", { name: "NVIDIA NIM documentation" }).first()).toHaveAttribute("href", /nvidia/);
  });

  test("admin settings switches the platform key scope and back", async ({ page }) => {
    await loginAs(page);
    await page.goto("/admin/settings");
    const scope = page.getByTestId("key-scope");
    await expect(scope.getByRole("button", { name: /serve everyone/ })).toHaveAttribute("aria-pressed", "true");
    await scope.getByRole("button", { name: /serve only the product/ }).click();
    await expect(scope.getByRole("button", { name: /serve only the product/ })).toHaveAttribute("aria-pressed", "true", { timeout: 10_000 });
    await page.reload();
    await expect(page.getByTestId("key-scope").getByRole("button", { name: /serve only the product/ })).toHaveAttribute("aria-pressed", "true");
    await page.getByTestId("key-scope").getByRole("button", { name: /serve everyone/ }).click();
    await expect(page.getByTestId("key-scope").getByRole("button", { name: /serve everyone/ })).toHaveAttribute("aria-pressed", "true", { timeout: 10_000 });
    await expect(page.getByTestId("providers-table")).toContainText("NVIDIA_NIM_API_KEY");
  });

  test("cost cockpit breaks spend down by key source", async ({ page }) => {
    await loginAs(page);
    await page.goto("/operate/cost");
    await page.getByRole("tab", { name: "Key source" }).click();
    await expect(page.locator("table thead")).toContainText("Key source");
  });
});
