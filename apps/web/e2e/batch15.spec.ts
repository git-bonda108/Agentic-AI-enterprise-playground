import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 15 cloud platforms: portal, CLI sign-in and step-by-step guides", () => {
  test("every platform shows its portal link and CLI sign-in, and the guide follows the framework and model", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/clouds?blueprint=doc-reconciliation");
    await expect(page.getByRole("heading", { level: 1, name: "Cloud platforms" })).toBeVisible();
    await expect(page.getByTestId("cloud-cards").getByRole("button")).toHaveCount(4);

    // Foundry is selected first: portal, sign-in commands and framework fit.
    await expect(page.getByTestId("platform-links").getByRole("link", { name: "Open Foundry portal" })).toHaveAttribute("href", "https://ai.azure.com");
    await expect(page.getByTestId("signin-block")).toContainText("azd auth login");
    await expect(page.getByTestId("signin-block")).toContainText("az login");
    await expect(page.getByTestId("framework-fit")).toContainText("Microsoft Agent Framework: first-class");

    // AgentCore: SSO sign-in and the npm CLI; the guide carries the deploy loop.
    await page.getByRole("button", { name: /AWS Bedrock AgentCore/ }).click();
    await expect(page.getByTestId("platform-links").getByRole("link", { name: "Open AgentCore console" })).toHaveAttribute("href", /console\.aws\.amazon\.com/);
    await expect(page.getByTestId("signin-block")).toContainText("aws sso login --profile <profile>");
    await expect(page.getByTestId("signin-block")).toContainText("npm install -g @aws/agentcore");
    await page.getByLabel("Framework to deploy").selectOption("langgraph");
    await expect(page.getByTestId("guide-steps")).toContainText("agentcore deploy", { timeout: 10_000 });
    await expect(page.getByTestId("guide-steps")).toContainText("1. Sign in to the AgentCore console");
    await expect(page.getByTestId("guide-summary")).toContainText("Gateway mode");
    await expect(page.getByTestId("guide-steps")).toContainText("PLAYGROUND_TOKEN");

    // Native mode with a Claude model switches the model step to Bedrock lookups.
    await page.getByLabel("Model to deploy with").selectOption("claude-sonnet-5");
    await page.getByTestId("guide-mode").getByRole("radio", { name: "Native provider endpoint" }).click();
    await expect(page.getByTestId("guide-summary")).toContainText("Native mode", { timeout: 10_000 });
    await expect(page.getByTestId("guide-steps")).toContainText("aws bedrock list-foundation-models");

    // Native mode with a model the cloud does not sell falls back to the gateway and says so.
    await page.getByLabel("Model to deploy with").selectOption("groq-gpt-oss-20b");
    await expect(page.getByTestId("guide-summary")).toContainText("Gateway mode", { timeout: 10_000 });
    await expect(page.getByTestId("guide-summary")).toContainText("keep the gateway mode");

    // Google and Anthropic: their sign-in commands and first-class paths.
    await page.getByRole("button", { name: /Google Agent Runtime/ }).click();
    await expect(page.getByTestId("signin-block")).toContainText("gcloud auth application-default login");
    await page.getByLabel("Framework to deploy").selectOption("adk");
    await expect(page.getByTestId("guide-steps")).toContainText("adk deploy agent_engine", { timeout: 10_000 });
    await page.getByRole("button", { name: /Anthropic Managed Agents/ }).click();
    await expect(page.getByTestId("signin-block")).toContainText("brew install anthropics/tap/ant");
    await expect(page.getByTestId("guide-steps")).toContainText("ant apply doc-reconciliation.md environment.yaml", { timeout: 10_000 });
    await expect(page.getByTestId("guide-summary")).toContainText("harness");

    // The guide downloads as markdown, and the self-hosting section explains the private repository.
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("guide-download").click()]);
    expect(download.suggestedFilename()).toBe("deploy-doc-reconciliation-adk-anthropic.md");
    await expect(page.getByTestId("self-hosting")).toContainText("infra/deploy.sh rg-ai-playground westeurope aiplay");
    await expect(page.getByTestId("self-hosting")).toContainText("private");
  });

  test("the how-to panel and the navigation name the page Cloud platforms", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/clouds");
    await expect(page.getByRole("link", { name: /Cloud platforms/ }).first()).toBeVisible();
    await page.getByRole("button", { name: "How to use this page" }).click();
    await expect(page.getByTestId("howto")).toContainText("Take an agent to a cloud runtime");
  });
});
