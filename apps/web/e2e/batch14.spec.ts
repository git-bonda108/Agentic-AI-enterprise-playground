import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 14 agents on every framework, built-in tools, how-to, traces", () => {
  test("frameworks page runs a project's smoke test in the sandbox and shows the gateway setup", async ({ page }) => {
    test.setTimeout(120_000);
    await loginAs(page);
    await page.goto("/discover/frameworks?blueprint=knowledge-qa");
    await page.getByRole("button", { name: /LangGraph/ }).click();
    await expect(page.getByTestId("file-agent.py")).toContainText("PLAYGROUND_BASE_URL", { timeout: 10_000 });
    await page.getByRole("button", { name: "Run smoke test" }).click();
    await expect(page.getByTestId("flavor-run-output")).toContainText("passed", { timeout: 90_000 });
    await expect(page.getByTestId("gateway-setup")).toContainText("openai/v1");
  });

  test("wizard offers built-in tools and the agent uses one in a run", async ({ page }) => {
    test.setTimeout(120_000);
    await loginAs(page);
    await page.goto("/build/agents");
    await page.getByRole("button", { name: "Create your own agent" }).click();
    const name = `Maths helper ${Date.now().toString(36)}`;
    await page.getByLabel("Agent name").fill(name);
    await page.getByLabel("Agent description").fill("Answers arithmetic with the calculate tool.");
    await page.getByLabel("Agent instructions").fill("You answer arithmetic questions. Always use the calculate tool and quote its result exactly.");
    await page.getByTestId("builtin-picker").getByLabel("Built-in tool calculate").check();
    await page.getByRole("button", { name: "Save agent" }).click();
    await expect(page.getByTestId("custom-agents")).toContainText(name, { timeout: 10_000 });
    await page.getByTestId("custom-agents").getByRole("button", { name: `Run ${name}` }).click();
    await page.getByLabel("Run input JSON").fill(JSON.stringify({ task: "calculate 6 * 7" }));
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByTestId("run-status")).toHaveText(/Completed/, { timeout: 90_000 });
    await expect(page.getByTestId("run-output")).toContainText("42");
  });

  test("how-to panel opens on the Agent Hub and traces show a run timeline", async ({ page }) => {
    await loginAs(page);
    await page.goto("/build/agents");
    await page.getByRole("button", { name: "How to use this page" }).click();
    await expect(page.getByTestId("howto")).toContainText("Create an agent, add tools, run it");
    await page.getByRole("button", { name: "Dismiss how-to" }).click();
    await page.goto("/operate/traces");
    await expect(page.getByRole("heading", { level: 1, name: "Traces" })).toBeVisible();
    await page.getByTestId("trace-run").first().click();
    await expect(page.getByTestId("trace-timeline")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("trace-detail")).toContainText("calls");
  });
});
