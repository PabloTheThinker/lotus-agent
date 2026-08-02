import { test, expect } from "@playwright/test";

test("setup banner appears when model is missing", async ({ page }) => {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        gateway: false,
        setup_needed: true,
        setup_hint: "Connect a model with Hermes: lotus setup",
        journey_ui: true,
        streaming: true,
      }),
    });
  });
  await page.route("**/api/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "test.nonce.sig" }),
    });
  });
  await page.route("**/api/prefs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        preferred_lang: "en",
        crisis_regions: ["US", "INTL"],
        source: "default",
      }),
    });
  });

  await page.goto("/");
  await expect(page.locator("#setupBanner")).toBeVisible();
  await expect(page.locator("#setupHint")).toContainText("lotus setup");
});

test("crisis banner localizes for Spanish cue", async ({ page }) => {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        gateway: true,
        setup_needed: false,
        journey_ui: true,
        streaming: true,
      }),
    });
  });
  await page.route("**/api/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "test.nonce.sig" }),
    });
  });
  await page.route("**/api/prefs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        preferred_lang: "es",
        crisis_regions: ["US", "INTL"],
      }),
    });
  });
  await page.route("**/api/crisis**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        lang: "es",
        region: "US",
        title: "Importas — busca ayuda humana ahora si estás en peligro.",
        body_html: "EE.UU. 988 · IASP",
      }),
    });
  });
  await page.route("**/api/chat/stream", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'data: {"choices":[{"delta":{"content":"Estoy contigo."}}]}\n\ndata: [DONE]\n\n',
    });
  });

  await page.goto("/");
  await page.click("#startBtn");
  await page.fill("#input", "quiero morir");
  await page.click("#sendBtn");
  await expect(page.locator("#crisisBanner")).toBeVisible({ timeout: 5000 });
  await expect(page.locator("#crisisTitle")).toContainText("Importas");
});
