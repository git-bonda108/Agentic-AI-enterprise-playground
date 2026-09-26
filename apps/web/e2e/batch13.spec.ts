import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 13 MCP Marketplace and Popular Git repos", () => {
  test("marketplace shows the featured shelf and per-client configuration for the playground server", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/connectors");
    await expect(page.getByRole("heading", { level: 1, name: "MCP Marketplace" })).toBeVisible();
    const shelf = page.getByTestId("featured-shelf");
    await expect(shelf.getByRole("button", { name: "Featured: Enterprise AI Playground" })).toBeVisible();
    await expect(page.getByTestId("directories")).toContainText("Official MCP registry");
    await shelf.getByRole("button", { name: "Featured: Enterprise AI Playground" }).click();
    const connect = page.getByTestId("connect-from");
    await expect(connect.getByRole("tab", { name: "Claude Code" })).toBeVisible({ timeout: 10_000 });
    await connect.getByRole("tab", { name: "Claude Code" }).click();
    await expect(page.getByTestId("install-snippet")).toContainText("claude mcp add --transport http enterprise-ai-playground");
    await connect.getByRole("tab", { name: "VS Code" }).click();
    await expect(page.getByTestId("install-snippet")).toContainText('"servers"');
    await connect.getByRole("tab", { name: "n8n" }).click();
    await expect(page.getByTestId("install-snippet")).toContainText("httpStreamable");
    await connect.getByRole("tab", { name: "Copilot Studio" }).click();
    await expect(connect).toContainText("Add an existing MCP server");
  });

  test("popular repos page groups repositories with stars, licences and reference implementations", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/repos");
    await expect(page.getByRole("heading", { level: 1, name: "Popular Git repos" })).toBeVisible();
    await expect(page.getByTestId("repo-group-reference-implementations")).toContainText("git-bonda108/");
    await expect(page.getByTestId("repo-group-visual-builders")).toContainText("langflow-ai/langflow");
    await expect(page.getByRole("article", { name: "langflow-ai/langflow" })).toContainText("MIT");
    await page.getByTestId("repo-categories").getByRole("tab", { name: /^MCP/ }).click();
    await expect(page.getByTestId("repo-group-mcp")).toBeVisible();
    await expect(page.getByTestId("repo-group-visual-builders")).toHaveCount(0);
    await page.getByLabel("Search repositories").fill("registry");
    await expect(page.getByRole("article", { name: "modelcontextprotocol/registry" })).toBeVisible({ timeout: 10_000 });
  });
});
