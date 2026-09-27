import { test, expect, type Page } from "@playwright/test";
import { loginAs } from "./helpers";
import { ALL_ITEMS } from "../src/lib/nav";
import { HOWTO } from "../src/lib/howto";

// Console noise that is not a defect: favicon probes, the JupyterLite frame's own worker logs, layout observers.
const IGNORED = [/favicon/i, /jupyterlite|pyodide|service worker/i, /ResizeObserver loop/i, /Download the React DevTools/i];

function watch(page: Page) {
  const errors: string[] = [];
  const failed: string[] = [];
  page.on("console", (m) => { if (m.type() === "error" && !IGNORED.some((re) => re.test(m.text()))) errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => { const u = r.url(); if (u.includes("/api/pg/") && r.status() >= 500) failed.push(`${r.status()} ${u}`); });
  return { errors, failed };
}

test.describe("Batch 17 documentation hub and full retest", () => {
  test("documentation hub lists the guides, searches them and renders one with images and links inside the product", async ({ page }) => {
    await loginAs(page);
    await page.goto("/docs");
    await expect(page.getByRole("heading", { level: 1, name: "Documentation" })).toBeVisible();
    await expect(page.getByTestId("docs-start-here")).toContainText("Guided tour");
    await expect(page.getByTestId("docs-build")).toContainText("Cloud platforms");
    await expect(page.getByTestId("docs-platform")).toContainText("Deployment");
    await expect(page.getByTestId("page-guides")).toContainText("Take an agent to a cloud runtime");
    await page.getByLabel("Search the documentation").fill("azd deploy");
    await expect(page.getByTestId("doc-search-results")).toContainText("Cloud platforms", { timeout: 10_000 });
    await page.getByTestId("docs-platform").getByRole("link", { name: /Deployment/ }).click();
    await expect(page).toHaveURL(/\/docs\/deployment$/);
    await expect(page.getByRole("heading", { level: 1, name: "Deployment" })).toBeVisible();
    await expect(page.getByTestId("doc-toc")).toContainText("Deploy in one command");
    const img = page.getByTestId("doc-body").locator("img").first();
    await expect(img).toHaveAttribute("src", /\/api\/pg\/v1\/docs\/images\/deployment\.png/);
    const image = await page.request.get("/api/pg/v1/docs/images/deployment.png");
    expect(image.headers()["content-type"]).toBe("image/png");
    await expect(page.getByTestId("doc-open-page")).toHaveAttribute("href", "/discover/clouds");
    await page.getByRole("link", { name: /Security/ }).last().click();
    await expect(page).toHaveURL(/\/docs\/security$/);
    // Cross-guide links resolve inside the hub, never to the repository.
    await page.goto("/docs/cloud-platforms");
    await expect(page.getByTestId("doc-body").getByRole("link", { name: "DEPLOYMENT.md" })).toHaveAttribute("href", "/docs/deployment");
    expect(await page.locator('a[href*="github.com/git-bonda108/Agentic-AI-enterprise-playground"]').count()).toBe(0);
  });

  test("how-to panels point at the hub, not at the repository", async ({ page }) => {
    await loginAs(page);
    await page.goto("/discover/clouds");
    await page.getByRole("button", { name: "How to use this page" }).click();
    await expect(page.getByTestId("howto").getByRole("link", { name: "Cloud platforms guide" })).toHaveAttribute("href", "/docs/cloud-platforms");
    expect(await page.getByTestId("howto").locator('a[href*="github.com/git-bonda108"]').count()).toBe(0);
  });

  test("every left-pane item renders its page with no console errors, no failed API calls, and a how-to where one exists", async ({ page }) => {
    test.setTimeout(240_000);
    await loginAs(page);
    const { errors, failed } = watch(page);
    const report: string[] = [];
    for (const item of ALL_ITEMS) {
      const before = errors.length + failed.length;
      await page.goto(item.href);
      const h1 = page.getByRole("heading", { level: 1 });
      await expect(h1).toBeVisible();
      if (item.href !== "/home") await expect(h1).toHaveText(item.title);
      if (HOWTO[item.href]) await expect(page.getByRole("button", { name: "How to use this page" })).toBeVisible();
      await page.waitForLoadState("networkidle").catch(() => {});
      const fresh = errors.length + failed.length - before;
      report.push(`${item.title} ${item.href} ${fresh === 0 ? "ok" : "ISSUES " + [...errors, ...failed].slice(-fresh).join(" | ")}`);
    }
    console.log(`RETEST\n${report.join("\n")}`);
    expect(errors, `console errors: ${errors.join(" | ")}`).toEqual([]);
    expect(failed, `failed API calls: ${failed.join(" | ")}`).toEqual([]);
  });
});
