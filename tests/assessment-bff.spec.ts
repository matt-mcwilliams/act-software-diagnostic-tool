import { expect, test } from "@playwright/test";

test.describe("assessment BFF", () => {
  test("reports local mode when the FastAPI base URL is absent", async ({ request }) => {
    const response = await request.get("/api/assessment/mode");

    expect(response.ok()).toBeTruthy();
    expect(response.headers()["cache-control"]).toContain("no-store");
    await expect(response.json()).resolves.toEqual({ mode: "local" });
  });

  test("rejects unknown assessment paths with a safe 404", async ({ request }) => {
    const response = await request.get("/api/assessment/not-a-real-route");

    expect(response.status()).toBe(404);
    await expect(response.json()).resolves.toEqual({
      error: { code: "not_found", message: "Assessment route not found." },
    });
  });
});
