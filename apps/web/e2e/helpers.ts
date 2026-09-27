import { expect, type Page } from "@playwright/test";

export async function loginAs(page: Page, name = "Satya Bonda") {
  await page.context().clearCookies();  // never sign in on top of a session a late response may have re-issued
  await page.goto("/login");
  await page.getByRole("button", { name: `Sign in as ${name}` }).click();
  await expect(page).toHaveURL(/\/home$/);
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: /Sign out/ }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  // Give responses still in flight at sign-out a moment to land before the cookies are dropped (the sign-out epoch makes
  // any that arrive later harmless); a bounded wait, because a page that keeps polling never reaches network idle.
  await page.waitForLoadState("networkidle", { timeout: 3000 }).catch(() => {});
  await page.context().clearCookies();
}
