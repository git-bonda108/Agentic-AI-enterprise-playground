import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 9 ship", () => {
  test("control room shows lanes, the ledger, reasoning and the outcome for a reconciliation run", async ({ page }) => {
    await loginAs(page);
    const created = await page.request.post("/api/pg/v1/runs", { data: { blueprint_id: "doc-reconciliation", input: { tolerance_pct: 2, auto_approve: true }, wait: true } });
    expect(created.status()).toBe(201);
    const run = await created.json();
    await page.goto(`/operate/runs/${run.id}`);
    await page.getByRole("tab", { name: "Control room" }).click();
    await expect(page.getByTestId("control-room")).toBeVisible();
    await expect(page.getByTestId("control-room")).toContainText("Deterministic");
    await expect(page.getByTestId("control-room")).toContainText("Agentic");
    await expect(page.getByTestId("control-room")).toContainText("Governed");
    await expect(page.getByTestId("ledger-table")).toContainText("INV-");
    await expect(page.getByTestId("reasoning-feed").locator("li")).not.toHaveCount(0);
    await expect(page.getByTestId("control-room")).toContainText("Completed under governance");
    await page.getByRole("tab", { name: "Graph" }).click();
    await expect(page.getByTestId("run-steps")).toBeVisible();
  });

  test("security headers reach the browser and the API refuses unknown callers", async ({ page }) => {
    await loginAs(page);
    const home = await page.request.get("/home");
    expect(home.headers()["x-frame-options"]).toBe("DENY");
    expect(home.headers()["x-content-type-options"]).toBe("nosniff");
    expect(home.headers()["x-powered-by"]).toBeUndefined();
    const api = await page.request.get("/api/pg/v1/models");
    expect(api.status()).toBe(200);
    expect(api.headers()["cache-control"]).toContain("no-store");
    const direct = await page.request.get("http://localhost:8011/v1/models", { headers: { "X-User-Id": "u1", "X-User-Email": "satya@playground.local" } });
    expect(direct.status()).toBe(401);
  });

  test("every section renders for a signed-in administrator", async ({ page }) => {
    await loginAs(page);
    for (const [path, needle] of [["/home", "Console"], ["/discover/blueprints", "blueprints across six families"], ["/build/agents", "runnable blueprints"], ["/evaluate/evals", "golden set"], ["/operate/cost", "Cost"], ["/community/leaderboard", "achievements"], ["/admin/settings", "Connect Claude Desktop"]] as const) {
      await page.goto(path);
      await expect(page.locator("body")).toContainText(needle);
    }
  });
});
