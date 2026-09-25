import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 5 faces", () => {
  test("notebooks page embeds the in-browser runtime and the sandbox executes code", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/notebooks?blueprint=doc-reconciliation");
    await expect(page.getByRole("heading", { level: 1, name: "Notebooks" })).toBeVisible();
    const frame = page.getByTestId("jupyterlite-frame");
    await expect(frame).toHaveAttribute("src", /\/jupyterlite\/lab\/index\.html/);
    await expect(page.getByTestId("lite-state")).toHaveText(/opened/, { timeout: 60_000 });
    await expect(page.frameLocator('[data-testid="jupyterlite-frame"]').locator(".lm-TabBar-tabLabel", { hasText: "doc-reconciliation.ipynb" })).toBeVisible({ timeout: 30_000 });
    const lite = await page.request.get("/jupyterlite/lab/index.html");
    expect(lite.status()).toBe(200);
    const nb = await page.request.get("/api/pg/v1/notebooks/blueprint/doc-reconciliation.ipynb");
    expect(nb.status()).toBe(200);
    expect((await nb.json()).cells.length).toBeGreaterThan(4);
    await page.getByRole("tab", { name: "Server sandbox" }).click();
    await page.getByLabel("Sandbox code").fill("print(6 * 7)");
    await page.getByRole("button", { name: "Run in sandbox" }).click();
    await expect(page.getByTestId("sandbox-output")).toContainText("42", { timeout: 30_000 });
    await expect(page.getByTestId("sandbox-output")).toContainText("exit 0");
  });

  test("frameworks page renders a project and serves the zip", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/frameworks?blueprint=sage-lens");
    await expect(page.getByTestId("framework-cards").getByRole("button")).toHaveCount(5);
    await page.getByRole("button", { name: /CrewAI/ }).click();
    await expect(page.getByTestId("file-agent.py")).toContainText("from crewai import Agent", { timeout: 10_000 });
    await page.getByRole("tab", { name: "test_smoke.py" }).click();
    await expect(page.getByTestId("file-test_smoke.py")).toContainText("def test_agent_module_parses");
    const zip = await page.request.get("/api/pg/v1/blueprints/sage-lens/flavor/crewai/download");
    expect(zip.status()).toBe(200);
    expect(zip.headers()["content-type"]).toContain("application/zip");
  });

  test("clouds page shows the pricing unit and the deploy commands", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/clouds?blueprint=doc-reconciliation");
    await expect(page.getByTestId("cloud-cards").getByRole("button")).toHaveCount(4);
    await expect(page.getByTestId("cloud-cards")).toContainText("$0.08 per session-hour");
    await page.getByRole("button", { name: /AWS Bedrock AgentCore/ }).click();
    await expect(page.getByTestId("deploy-script")).toContainText("agentcore launch", { timeout: 10_000 });
    await page.getByRole("button", { name: /Microsoft Foundry/ }).click();
    await expect(page.getByTestId("deploy-script")).toContainText("PromptAgentDefinition");
  });

  test("the wizard creates an agent that runs and exports", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/agents");
    await page.getByRole("button", { name: "Create your own agent" }).click();
    // Unique per run: the e2e database survives between runs, so a fixed name would match older agents too.
    const agentName = `Travel buddy ${Date.now().toString(36)}`;
    await page.getByLabel("Agent name").fill(agentName);
    await page.getByLabel("Agent description").fill("Answers travel policy questions for new joiners.");
    await page.getByLabel("Agent instructions").fill("You answer travel questions from the policies provided and always cite the policy id.");
    await page.getByLabel("Company policies").check();
    await page.getByLabel("Starter prompt 1").fill("What is the hotel limit per night?");
    await page.getByRole("button", { name: "Save agent" }).click();
    await expect(page.getByTestId("custom-agents")).toContainText(agentName, { timeout: 10_000 });
    const exportRes = await page.request.get((await page.getByRole("link", { name: `Export ${agentName} for Copilot Studio` }).getAttribute("href"))!);
    expect(exportRes.status()).toBe(200);
    expect((await exportRes.json()).version).toBe("v1.5");
    await page.getByRole("button", { name: `Run ${agentName}` }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 20_000 });
    await expect(page.getByTestId("run-output")).toContainText("POL-001");
  });
});
