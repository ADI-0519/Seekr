import { expect, test } from "@playwright/test";

test("web app serves root page", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toBeVisible();
});
