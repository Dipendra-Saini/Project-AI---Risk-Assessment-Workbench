// Demo rehearsal + deck screenshots against a seeded stack (make up, or make seed + api + web).
//   BASE=http://localhost:8080 node e2e/screenshots.mjs
// Writes docs/assets/*.png. Fails loudly if any demo step is not in the expected state.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE ?? "http://localhost:8080";
const OUT = fileURLToPath(new URL("../../../docs/assets/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const steps = [];

async function as(username, fn) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.getByTestId(`persona-${username}`).click();
  await page.getByTestId("case-list").waitFor();
  try {
    await fn(page);
  } finally {
    await ctx.close();
  }
}

const TITLES = {
  G01: "Cross-border instant payouts for gig workers",
  G02: "Retail crypto trading and custody",
  G13: "IT hosting vendor in Zelrania",
  G17: "Cash-funded remittances to Veridia",
};

async function openCase(page, golden) {
  await page.locator('[data-testid^="case-row-"]').getByRole("link", { name: TITLES[golden] }).first().click();
  await page.getByTestId("case-view").waitFor();
  await page.waitForLoadState("networkidle");
}

async function shot(page, name, opts = {}) {
  await page.screenshot({ path: `${OUT}${name}.png`, ...opts });
  steps.push(name);
}

await (async () => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.getByTestId("persona-priya").waitFor();
  await shot(page, "01-login");
  await ctx.close();
})();

await as("priya", async (page) => {
  await openCase(page, "G13");
  await page.getByTestId("extraction-table").waitFor();
  await shot(page, "02-po-intake-g0");
});

await as("arjun", async (page) => {
  await shot(page, "03-analyst-queue");
  await openCase(page, "G01");
  await page.getByTestId("residual-tier").waitFor();
  await page.getByTestId("awaiting-ack").waitFor();
  await shot(page, "04-analyst-g01");
  await shot(page, "04-analyst-g01-full", { fullPage: true });
  const chip = page.locator('[data-testid^="section-"] [data-testid="citation-chip"]').nth(1);
  await chip.scrollIntoViewIfNeeded();
  await chip.click();
  await page.getByTestId("chunk-text").waitFor();
  await shot(page, "05-citation-source");
  await page.keyboard.press("Escape");
  await page.goto(`${BASE}/`);
  await openCase(page, "G17");
  await page.getByTestId("case-warnings").waitFor();
  await shot(page, "06-injection-g17");
});

await as("sara", async (page) => {
  await openCase(page, "G01");
  const ack = page.locator('[data-testid^="ack-"]').first();
  await ack.waitFor();
  await ack.scrollIntoViewIfNeeded();
  await shot(page, "07-second-analyst-ack");
});

await as("meera", async (page) => {
  await openCase(page, "G02");
  await page.getByTestId("votes").waitFor();
  await page.getByTestId("quorum").scrollIntoViewIfNeeded();
  await shot(page, "08-committee-g02", { fullPage: true });
  await page.getByTestId("nav-audit").click();
  await page.getByTestId("verify-chain").click();
  await page.getByTestId("verify-result").waitFor();
  await shot(page, "09-audit-verify");
  await page.getByTestId("nav-tokens").click();
  await page.getByTestId("token-table").waitFor();
  await shot(page, "10-tokens");
});

await browser.close();
console.log(`ok: ${steps.length} screenshots in docs/assets/: ${steps.join(", ")}`);
