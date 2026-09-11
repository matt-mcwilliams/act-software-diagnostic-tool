import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

test("the home page introduces the ACT learning loop", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("ACT Adaptive");
  await expect(page.getByRole("heading", { name: "Find the skill to work on next." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Start a diagnostic" })).toBeVisible();
  await expect(page.getByText("Diagnose")).toBeVisible();
  await expect(page.getByText("Learn + practice")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Reassess" })).toBeVisible();
});

test("a student can complete an English diagnostic and resume saved work", async ({ page }) => {
  await page.goto("/diagnostic/english");
  await expect(page.getByRole("heading", { name: "Answer at your own pace." })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Question 1 of 8")).toBeVisible({ timeout: 15000 });

  await page.getByRole("radio").first().click();
  await page.reload();
  await expect(page.getByRole("radio").first()).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText("Saved")).toBeVisible();
});

test("a student can complete the English diagnose-to-reassess loop", async ({ page }) => {
  await page.goto("/diagnostic/english");
  await expect(page.getByText("Question 1 of 8")).toBeVisible({ timeout: 15000 });

  for (let index = 0; index < 7; index += 1) {
    await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: "Next question" }).click();
  }
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Submit diagnostic" }).click();
  await page.waitForURL("**/results/english");

  await expect(page.getByRole("heading", { name: "Here is what to work on next." })).toBeVisible();
  await expect(page.getByText("Recommended targets")).toBeVisible();
  await page.getByRole("link", { name: "Learn this skill" }).first().click();
  await page.waitForURL("**/learn/english/**");
  await expect(page.getByRole("heading", { name: "Unnecessary Punctuation" })).toBeVisible();
  await page.getByRole("link", { name: "Continue to practice" }).click();
  await page.waitForURL("**/practice/english/**");

  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Next question" }).click();
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Continue to reassessment" }).click();
  await page.waitForURL("**/reassess/english/**");
  await expect(page.getByText("Feedback will appear after you submit the set.")).toBeVisible();

  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Next question" }).click();
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Submit reassessment" }).click();
  await expect(page.getByText("Your evidence has been updated.")).toBeVisible();
  await expect(page.getByText("Current skill estimate")).toBeVisible();
});

test("diagnostic content does not include answer keys", async ({ request }) => {
  const response = await request.get("/api/prototype/questions?subject=english&purpose=diagnostic");
  expect(response.ok()).toBeTruthy();
  const body = await response.text();
  expect(body).not.toContain("correctChoiceId");
  expect(body).not.toContain("failureModeByChoice");
  expect(body).not.toContain("explanation");
});

test("the shared diagnostic and results flow supports Math", async ({ page }) => {
  await page.goto("/diagnostic/math");
  await expect(page.getByText("Question 1 of 8")).toBeVisible({ timeout: 15000 });

  for (let index = 0; index < 7; index += 1) {
    await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: "Next question" }).click();
  }
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Submit diagnostic" }).click();
  await page.waitForURL("**/results/math");
  await expect(page.getByRole("heading", { name: "Here is what to work on next." })).toBeVisible();
  await expect(page.getByText("Math results")).toBeVisible();
  await expect(page.getByRole("link", { name: "Learn this skill" }).first()).toBeVisible();
});
