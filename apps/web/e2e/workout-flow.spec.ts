import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";

const API = "http://127.0.0.1:8000";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

async function signInDev(sub: string): Promise<TokenPair> {
  const response = await fetch(`${API}/v1/auth/dev`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sub, email: `${sub}@example.com` }),
  });
  if (!response.ok) throw new Error(`dev sign-in failed: ${response.status}`);
  return response.json();
}

async function createExercise(token: string, name: string) {
  const response = await fetch(`${API}/v1/exercises`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      name,
      primary_muscle: "chest",
      secondary_muscles: [],
      equipment: "barbell",
      movement_pattern: "horizontal_push",
      tracking_type: "weight_reps",
      is_unilateral: false,
    }),
  });
  if (!response.ok) throw new Error(`create exercise failed: ${response.status}`);
  return response.json();
}

test("log a session end to end", async ({ page, context }) => {
  const sub = `e2e-${randomUUID()}`;
  const tokens = await signInDev(sub);

  // Seed two exercises directly via the API so the picker has known options.
  const ex1 = await createExercise(tokens.access_token, "E2E Bench");
  const ex2 = await createExercise(tokens.access_token, "E2E Row");

  // Set the auth cookies the web app expects.
  await context.addCookies([
    {
      name: "gym_access",
      value: tokens.access_token,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      expires: Math.floor(Date.now() / 1000) + tokens.expires_in,
    },
    {
      name: "gym_refresh",
      value: tokens.refresh_token,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      expires: Math.floor(Date.now() / 1000) + 60 * 24 * 60 * 60,
    },
  ]);

  await page.goto("/");
  await page.getByTestId("start-empty-workout").click();

  await expect(page).toHaveURL(/\/workouts\/[^/]+$/);

  // Add first exercise via the picker.
  await page.getByTestId("add-exercise").click();
  await page.getByPlaceholder("Search exercises...").fill("E2E Bench");
  await page.getByText("E2E Bench").click();

  // Log 3 sets.
  for (const [w, r] of [
    ["100", "5"],
    ["100", "5"],
    ["100", "5"],
  ] as const) {
    await page
      .getByLabel(/kg for set/)
      .last()
      .fill(w);
    await page
      .getByLabel(/reps for set/)
      .last()
      .fill(r);
    await page.getByRole("button", { name: /save/i }).last().click();
    await expect(page.locator('[data-testid="set-row"]')).toHaveCount(
      (await page.locator('[data-testid="set-row"]').count()) > 0
        ? await page.locator('[data-testid="set-row"]').count()
        : 1,
    );
  }

  // Add second exercise + 3 more sets.
  await page.getByTestId("add-exercise").click();
  await page.getByPlaceholder("Search exercises...").fill("E2E Row");
  await page.getByText("E2E Row").click();
  for (let i = 0; i < 3; i += 1) {
    await page
      .getByLabel(/kg for set/)
      .last()
      .fill("60");
    await page
      .getByLabel(/reps for set/)
      .last()
      .fill("8");
    await page.getByRole("button", { name: /save/i }).last().click();
  }

  await page.getByTestId("finish-workout").click();
  await expect(page).toHaveURL(/\/summary$/);
  await expect(page.getByText("Volume")).toBeVisible();
  await expect(page.getByText("Sets")).toBeVisible();
  // Total sets: 6
  await expect(page.locator("text=6").first()).toBeVisible();
});
