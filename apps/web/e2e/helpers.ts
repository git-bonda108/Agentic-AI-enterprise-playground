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
  // A response still in flight at sign-out can re-issue the rolling session cookie; drop everything to be sure.
  await page.context().clearCookies();
}
