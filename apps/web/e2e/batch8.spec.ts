import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Batch 8 community and adoption", () => {
  test("showcase: draft a post from a run with the writer agent, publish, like and comment", async ({ page }) => {
    await loginAs(page);
    const run = await page.request.post("/api/pg/v1/runs", { data: { blueprint_id: "knowledge-qa", input: { question: "What is the hotel limit per night?" }, wait: true } });
    expect(run.status()).toBe(201);
    await page.goto("/community/showcase");
    await expect(page.getByRole("heading", { level: 1, name: "Showcase" })).toBeVisible();
    await page.getByRole("button", { name: "Publish to showcase" }).click();
    await page.getByRole("button", { name: "Draft with the writer agent" }).click();
    await expect(page.getByLabel("Post title")).not.toHaveValue("", { timeout: 30_000 });
    const title = `Policy answers ${Date.now().toString(36)}`;
    await page.getByLabel("Post title").fill(title);
    await page.getByLabel("Post outcome").fill("Answered from policy in two seconds");
    await page.getByRole("button", { name: "Publish post" }).click();
    await expect(page.getByTestId("showcase-cards")).toContainText(title, { timeout: 10_000 });
    await page.getByRole("button", { name: `Like ${title}` }).click();
    await expect(page.getByRole("button", { name: `Unlike ${title}` })).toContainText("1");
    await page.getByRole("button", { name: `Open ${title}` }).click();
    await page.getByLabel("Comment", { exact: true }).fill("Great use of citations");
    await page.getByRole("button", { name: "Post comment" }).click();
    await expect(page.getByTestId("comments")).toContainText("Great use of citations");
  });

  test("challenges: open, submit, judge by rubric, close and award the badge", async ({ page }) => {
    await loginAs(page);
    await page.goto("/community/challenges");
    await page.getByRole("button", { name: "Open a challenge" }).click();
    const title = `Policy sprint ${Date.now().toString(36)}`;
    await page.getByLabel("Challenge title").fill(title);
    await page.getByLabel("Challenge brief").fill("Build an agent that answers policy questions with a citation.");
    await page.getByLabel("Shared cases").fill("What is the hotel limit per night? => POL-001\nWhat do I need for a purchase over 50,000 USD? => POL-002");
    await page.getByRole("button", { name: "Create challenge" }).click();
    await expect(page.getByTestId("challenge-detail")).toContainText(title, { timeout: 10_000 });
    await page.getByLabel("Agent to submit").selectOption("knowledge-qa");
    await page.getByLabel("Submission note").fill("The built-in one");
    await page.getByRole("button", { name: "Submit entry" }).click();
    await expect(page.getByTestId("standings")).toContainText("pending", { timeout: 10_000 });
    await page.getByRole("button", { name: "Judge submissions" }).click();
    await expect(page.getByTestId("standings")).not.toContainText("pending", { timeout: 60_000 });
    await expect(page.getByTestId("standings")).toContainText("Knowledge Q&A");
    await expect(page.getByTestId("standings")).toContainText("100%");  // both shared cases must pass, so the input key reached the agent
    await page.getByRole("button", { name: "Close challenge" }).click();
    await expect(page.getByTestId("standings").getByLabel("Winner")).toBeVisible({ timeout: 10_000 });
    await page.goto("/community/leaderboard");
    await expect(page.getByTestId("achievements")).toContainText("Champion");
    await expect(page.getByTestId("leaderboard-table")).toContainText("Satya Bonda");
    await page.getByRole("tab", { name: "Departments" }).click();
    await expect(page.getByTestId("leaderboard-table")).toContainText("AI Platform");
  });

  test("adoption: hours per feature, ROI matrix, assumptions and the digest agent", async ({ page }) => {
    await loginAs(page);
    await page.goto("/operate/adoption");
    await expect(page.getByRole("heading", { level: 1, name: "Adoption" })).toBeVisible();
    await expect(page.getByTestId("adoption-kpis")).toContainText("Outcomes");
    await expect(page.getByTestId("feature-table")).toContainText("Agent runs");
    await expect(page.getByTestId("roi-matrix")).toContainText("AI Platform");
    await page.getByLabel("Minutes saved per completed agent run").fill("40");
    await page.getByRole("button", { name: "Save assumptions" }).click();
    await expect(page.getByLabel("Minutes saved per completed agent run")).toHaveValue("40", { timeout: 10_000 });
    await page.getByRole("button", { name: "Generate digest" }).click();
    await expect(page.getByTestId("digest")).toContainText("Adoption digest agent", { timeout: 60_000 });
    await expect(page.getByTestId("digest").locator("ol li")).toHaveCount(3);
  });
});
