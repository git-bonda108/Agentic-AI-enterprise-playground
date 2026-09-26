import { test, expect } from "@playwright/test";
import { loginAs, logout } from "./helpers";

test.describe("Batch 2 catalog, routing, cost, admin", () => {
  test("model catalog filters and opens the playground with a preselected model", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/models");
    await expect(page.getByRole("heading", { level: 1, name: "Models" })).toBeVisible();
    await expect(page.getByTestId("model-grid").getByRole("article")).toHaveCount(30);
    await page.getByRole("button", { name: "DeepSeek", exact: true }).click();
    await expect(page.getByTestId("model-grid").getByRole("article")).toHaveCount(2);
    await page.getByRole("button", { name: "Table view" }).click();
    await expect(page.getByTestId("model-table")).toContainText("DeepSeek V4 Flash");
    await page.getByRole("link", { name: "Try", exact: true }).first().click();
    await expect(page).toHaveURL(/\/build\/playground\?model=deepseek/);
    await expect(page.getByRole("button", { name: "Choose model" })).toContainText("DeepSeek");
  });

  test("smart routing previews the choice and tags the reply", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/playground?model=smart");
    await expect(page.getByRole("button", { name: "Choose model" })).toContainText("Smart routing");
    await page.getByLabel("Prompt", { exact: true }).fill("Translate 'good evening' to German.");
    await expect(page.getByTestId("route-preview")).toContainText("economy", { timeout: 10_000 });
    await expect(page.getByTestId("route-preview")).toContainText("saves");
    await page.keyboard.press("Enter");
    await expect(page.getByText(/Fake reply from/)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("usage-chip").first()).toContainText("smart · saved");
  });

  test("cost cockpit shows KPIs and switches layers", async ({ page }) => {
    await loginAs(page);
    await page.goto("/operate/cost");
    await expect(page.getByRole("heading", { level: 1, name: "Cost" })).toBeVisible();
    await expect(page.getByText("Saved by Smart routing")).toBeVisible();
    await expect(page.getByTestId("cost-table")).toContainText(/claude|gpt|deepseek/i);
    await page.getByRole("tab", { name: "User" }).click();
    await expect(page.getByTestId("cost-table")).toContainText("Satya Bonda");
    await page.getByRole("tab", { name: "Feature" }).click();
    await expect(page.getByTestId("cost-table")).toContainText("chat");
  });

  test("admin can change a role and the policy blocks a frontier model", async ({ page }) => {
    await loginAs(page);
    await page.goto("/admin/users");
    await expect(page.getByTestId("users-table")).toContainText("Satya Bonda");
    await page.goto("/admin/policies");
    await expect(page.getByRole("heading", { level: 2, name: "Explorer" })).toBeVisible();
    await page.goto("/admin/settings");
    await expect(page.getByTestId("providers-table")).toContainText("ANTHROPIC_API_KEY");
  });

  test("a tiny personal cap blocks the next call and raises an alert", async ({ page }) => {
    await loginAs(page, "Carlos Mendes");
    await page.goto("/build/playground");
    await page.getByLabel("Prompt", { exact: true }).fill("one small call before the cap");
    await page.keyboard.press("Enter");
    await expect(page.getByText(/Fake reply from/)).toBeVisible({ timeout: 15_000 });

    await logout(page);
    await loginAs(page, "Satya Bonda");
    await page.goto("/admin/budgets");
    await page.getByLabel("Person to cap").selectOption({ label: "Carlos Mendes" });
    await page.getByLabel("Cap amount", { exact: true }).fill("0.000001");
    await page.getByRole("button", { name: "Add person cap" }).click();
    await page.getByRole("button", { name: "Save budgets" }).click();
    await expect(page.getByText("Budgets saved")).toBeVisible();

    await logout(page);
    await loginAs(page, "Carlos Mendes");
    await page.goto("/build/playground");
    await page.getByLabel("Prompt", { exact: true }).fill("this one should be blocked");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("alert").filter({ hasText: /monthly cap/ })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /Notifications, \d+ unread/ })).toBeVisible();

    // restore Carlos so other runs are unaffected
    await logout(page);
    await loginAs(page, "Satya Bonda");
    await page.goto("/admin/budgets");
    await page.getByRole("button", { name: "Remove cap for Carlos Mendes" }).click();
    await page.getByRole("button", { name: "Save budgets" }).click();
    await expect(page.getByText("Budgets saved")).toBeVisible();
  });
});
