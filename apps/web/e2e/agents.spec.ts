import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 3 agent hub and runs", () => {
  test("document reconciliation pauses for a decision and completes after approval", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/agents");
    await expect(page.getByRole("heading", { level: 1, name: "Agent Hub" })).toBeVisible();
    await expect(page.getByTestId("blueprint-grid").getByRole("article")).toHaveCount(8);  // six domain blueprints plus two platform agents
    await page.getByRole("button", { name: "Run Document reconciliation" }).click();
    await page.getByRole("radio", { name: "Three suspicious invoices" }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page).toHaveURL(/\/operate\/runs\//);
    await expect(page.getByTestId("review-panel")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("review-panel")).toContainText("INV-9002");
    await page.getByRole("radio", { name: "approve", exact: true }).click();
    await page.getByLabel("Notes for the audit trail").fill("Reviewed in the demo");
    await page.getByRole("button", { name: "Submit decision" }).click();
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 20_000 });
    await expect(page.getByTestId("run-output")).toContainText(/fake|summary|invoice/i);
    await expect(page.getByTestId("run-steps")).toContainText("Human decision: approve");
    await expect(page.getByTestId("run-cost")).not.toHaveText("$0.00");
  });

  test("sage lens asks for clarification on a vague question", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/agents?blueprint=sage-lens");
    await page.getByRole("radio", { name: /Vague question/ }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByTestId("review-panel")).toContainText("Which company", { timeout: 20_000 });
    await page.getByRole("radio", { name: "Tesla" }).click();
    await page.getByRole("button", { name: "Submit decision" }).click();
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 20_000 });
    await expect(page.getByTestId("run-steps")).toContainText("Clarified with the user: Tesla");
  });

  test("runs list and data page show what happened", async ({ page }) => {
    await loginAs(page);
    await page.goto("/operate/runs");
    await expect(page.getByTestId("runs-table")).toContainText("Document reconciliation");
    await page.goto("/build/data");
    await expect(page.getByTestId("datasets")).toContainText("Supplier invoices");
    await expect(page.getByTestId("datasets")).toContainText("sales.csv");
    await page.goto("/operate/cost");
    await page.getByRole("tab", { name: "Feature" }).click();
    await expect(page.getByTestId("cost-table")).toContainText("agent");
  });
});
