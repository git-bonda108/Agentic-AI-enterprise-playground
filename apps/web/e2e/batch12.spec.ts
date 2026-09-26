import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 12 two ways to build", () => {
  test("blueprints are categorised as Gen AI or Agentic AI and the detail offers both tracks", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/blueprints");
    await expect(page.getByTestId("category-tabs")).toBeVisible();
    await page.getByTestId("category-tabs").getByRole("tab", { name: /^Agentic AI/ }).click();
    await expect(page.getByTestId("catalog-grid").getByRole("article").first()).toBeVisible();
    await expect.poll(async () => (await page.getByTestId("category-badge").allTextContents()).every((b) => b === "Agentic AI")).toBe(true);
    expect((await page.getByTestId("category-badge").count())).toBeGreaterThan(10);
    await page.getByTestId("category-tabs").getByRole("tab", { name: /^All/ }).click();
    await page.getByRole("tab", { name: /^Domain/ }).click();
    await page.getByRole("button", { name: "Document reconciliation" }).click();
    const tracks = page.getByTestId("build-tracks");
    await expect(tracks).toContainText("Agentic AI blueprint");
    await expect(tracks.getByRole("link", { name: "Langflow flow" })).toHaveAttribute("href", /\/discover\/low-code\?blueprint=doc-reconciliation&studio=langflow/);
    await expect(tracks.getByRole("link", { name: "Notebook" })).toHaveAttribute("href", /\/build\/notebooks\?blueprint=doc-reconciliation/);
  });

  test("low-code studios generate a Langflow flow, an n8n workflow and a Copilot Studio recipe", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/low-code?blueprint=doc-reconciliation&studio=langflow");
    await expect(page.getByRole("heading", { level: 1, name: "Low-code studios" })).toBeVisible();
    await expect(page.getByTestId("studio-cards").getByRole("button")).toHaveCount(3);
    await expect(page.getByTestId("studio-category")).toHaveText("Agentic AI");
    await expect(page.getByTestId("artefact-json")).toContainText('"ChatInput"', { timeout: 15_000 });
    await expect(page.getByTestId("artefact-json")).toContainText("never invent numbers");
    await expect(page.getByTestId("studio-steps")).toContainText("Upload the downloaded flow JSON");
    await expect(page.getByRole("link", { name: "Download Langflow flow.json" })).toHaveAttribute("href", "/api/pg/v1/lowcode/doc-reconciliation/langflow?download=1");
    await page.getByTestId("studio-cards").getByRole("button", { name: /n8n/ }).click();
    await expect(page.getByTestId("artefact-json")).toContainText("mcpClientTool", { timeout: 15_000 });
    await expect(page.getByTestId("artefact-json")).toContainText("n8n-nodes-base.wait");
    await page.getByTestId("studio-cards").getByRole("button", { name: /Copilot Studio/ }).click();
    const recipe = page.getByTestId("copilot-recipe");
    await expect(recipe).toContainText("Workflow nodes", { timeout: 15_000 });
    await expect(recipe).toContainText("Human review");
    await expect(recipe.getByRole("link", { name: "Request for information node" })).toHaveAttribute("href", /learn\.microsoft\.com\/en-us\/microsoft-copilot-studio\/workflows-experience\/flows-request-for-information/);
    await expect(page.getByTestId("code-track")).toContainText("Frameworks");
    const landscape = page.getByTestId("landscape");
    await expect(landscape.locator("tbody tr")).toHaveCount(9);
    await expect(landscape).toContainText("Sustainable Use Licence");
    const download = await page.request.get("/api/pg/v1/lowcode/doc-reconciliation/n8n?download=1");
    expect(download.status()).toBe(200);
    expect(download.headers()["content-disposition"]).toContain("doc-reconciliation-n8n.json");
  });
});
