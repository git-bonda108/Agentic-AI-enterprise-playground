import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers";
import { ALL_ITEMS } from "../src/lib/nav";

test.describe("Batch 0 smoke", () => {
  test("unauthenticated visit redirects to login", async ({ page }) => {
    await page.goto("/home");
    await expect(page).toHaveURL(/\/login\?next=%2Fhome$/);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("dev user can sign in and sees the console", async ({ page }) => {
    await loginAs(page);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Good (morning|afternoon|evening|night)|Welcome/);
    await expect(page.getByText("Organization credits")).toBeVisible();
    await expect(page.getByRole("link", { name: /Fable 5.1 by Anthropic/ })).toBeVisible();
  });

  test("every navigation item renders its page", async ({ page }) => {
    await loginAs(page);
    for (const item of ALL_ITEMS) {
      await page.goto(item.href);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      if (item.href !== "/home") {
        await expect(page.getByRole("heading", { level: 1 })).toHaveText(item.title);
      }
    }
  });

  test("sidebar collapses and command palette opens", async ({ page }) => {
    await loginAs(page);
    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    await expect(page.getByRole("button", { name: "Expand sidebar" })).toBeVisible();
    await page.keyboard.press("ControlOrMeta+k");
    await expect(page.getByPlaceholder(/Search pages/)).toBeVisible();
    await page.getByPlaceholder(/Search pages/).fill("Cost");
    await page.getByRole("option", { name: /Cost/ }).click();
    await expect(page).toHaveURL(/\/operate\/cost$/);
  });

  test("sign out returns to login", async ({ page }) => {
    await loginAs(page);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: /Sign out/ }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});
