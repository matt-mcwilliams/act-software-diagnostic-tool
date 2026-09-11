import { expect, test } from "@playwright/test";

test("the diagnostic workspace is ready for a new run", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/ACT Diagnostic Tool/);
  await expect(
    page.getByRole("heading", { name: /Find the fault before it finds you/ }),
  ).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Diagnostic name" })).toBeVisible();
  await expect(page.getByText("AI not connected")).toBeVisible();
});
