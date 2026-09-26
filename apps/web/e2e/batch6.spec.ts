import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 6 connectors, knowledge, skills", () => {
  test("connectors page lists the registry, tests a connection and lets an admin approve", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/connectors");
    await expect(page.getByRole("heading", { level: 1, name: "Connectors" })).toBeVisible();
    await expect(page.getByTestId("connector-cards").getByRole("button").first()).toBeVisible();
    await page.getByLabel("Search connectors").fill("Enterprise AI Playground");
    await page.getByRole("button", { name: "Enterprise AI Playground", exact: true }).click();
    await expect(page.getByTestId("install-snippet")).toContainText("/mcp");
    await page.getByRole("button", { name: "Test connection" }).click();
    await expect(page.getByTestId("probe-result")).toContainText("Connected to enterprise-ai-playground", { timeout: 15_000 });
    await expect(page.getByTestId("probe-result")).toContainText("run_blueprint");
    await page.keyboard.press("Escape");
    await page.getByLabel("Search connectors").fill("github-mcp-server");
    await page.getByRole("button", { name: /GitHub/i }).first().click();
    await expect(page.getByRole("button", { name: "Block connector" })).toBeVisible();
    await page.getByRole("button", { name: "Block connector" }).click();
    await expect(page.getByRole("dialog")).toContainText("blocked");
    await page.getByRole("button", { name: "Approve connector" }).click();
    await expect(page.getByRole("dialog")).toContainText("approved");
  });

  test("skills page searches packs and hands one to the wizard", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/skills");
    await expect(page.getByRole("heading", { level: 1, name: "Skills" })).toBeVisible();
    await page.getByLabel("Search skills").fill("tdd");
    const first = page.getByTestId("skill-cards").getByRole("button").first();
    await expect(first).toHaveAttribute("aria-label", /tdd/i, { timeout: 10_000 });  // wait for the debounced search to apply
    const name = (await first.getAttribute("aria-label"))!;
    await first.click();
    await expect(page.getByTestId("skill-body")).toBeVisible();
    await page.getByRole("link", { name: "Attach to a new agent" }).click();
    await expect(page).toHaveURL(/\/build\/agents\?skill=/);
    await expect(page.getByRole("dialog")).toContainText("Create your own agent");
    await expect(page.getByTestId("skill-picker").getByLabel(`Skill ${name}`)).toBeChecked();
  });

  test("knowledge space: create, add text, search, ask, map a repository and draw the graph", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/knowledge");
    await expect(page.getByRole("heading", { level: 1, name: "Knowledge" })).toBeVisible();
    await page.getByRole("button", { name: "New Knowledge Space" }).click();
    const spaceName = `Travel desk ${Date.now().toString(36)}`;
    await page.getByLabel("Space name").fill(spaceName);
    await page.getByRole("button", { name: "Create space" }).click();
    await expect(page.getByTestId("space-detail")).toContainText(spaceName, { timeout: 10_000 });
    await page.getByLabel("Document title").fill("Travel policy");
    await page.getByLabel("Document text").fill("Hotel stays are reimbursed up to 220 USD per night in major cities and 150 USD elsewhere.\n\nTaxi rides are reimbursed with a receipt.");
    await page.getByRole("button", { name: "Add text" }).click();
    await expect(page.getByTestId("documents-table")).toContainText("Travel policy", { timeout: 15_000 });
    await page.getByRole("tab", { name: "Search" }).click();
    await page.getByLabel("Search query").fill("hotel per night");
    await page.getByRole("button", { name: "Search space" }).click();
    await expect(page.getByTestId("search-hits")).toContainText("220 USD", { timeout: 10_000 });
    await page.getByRole("tab", { name: "Ask" }).click();
    await page.getByLabel("Question").fill("What is the hotel limit per night?");
    await page.getByRole("button", { name: "Ask space" }).click();
    await expect(page.getByTestId("ask-answer")).toContainText("Grounded", { timeout: 30_000 });
    await page.getByRole("tab", { name: "Add content" }).click();
    await page.getByRole("button", { name: "Map repository" }).click();
    await expect(page.getByTestId("documents-table")).toContainText("Repository:", { timeout: 60_000 });
    await page.getByRole("tab", { name: "Graph" }).click();
    await expect(page.getByTestId("code-graph")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("graph-side")).toContainText(/\d+ nodes · \d+ edges/);
  });

  test("settings issues a personal token for external MCP clients", async ({ page }) => {
    await loginAs(page);
    await page.goto("/admin/settings");
    await expect(page.getByTestId("tokens-panel")).toBeVisible();
    await page.getByLabel("Token name").fill("Claude Desktop");
    await page.getByRole("button", { name: "Create token" }).click();
    await expect(page.getByTestId("fresh-token")).toContainText("pgk_", { timeout: 10_000 });
    await expect(page.getByTestId("fresh-token")).toContainText("enterprise-ai-playground");
    await expect(page.getByTestId("token-list")).toContainText("Claude Desktop");
  });
});
