import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = process.env.FORGEOPS_URL;
if (!baseUrl) throw new Error("FORGEOPS_URL is required");

const outDir = "docs/images/live";
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
page.setDefaultTimeout(30_000);

async function waitForApp() {
  for (let attempt = 1; attempt <= 30; attempt += 1) {
    try {
      const response = await page.request.get(`${baseUrl}/api/backend/health`);
      if (response.ok()) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 10_000));
  }
  throw new Error("Live ForgeOps deployment did not become ready");
}

await waitForApp();
await page.goto(baseUrl, { waitUntil: "networkidle" });
await page.screenshot({ path: `${outDir}/01-mission-control.png`, fullPage: true });

await page.getByRole("button", { name: /new mission/i }).click();
await page.getByLabel("Mission title").fill("Analyze a simulated API deployment failure");
await page.getByLabel("Mission description").fill(
  "Treat this as a simulated, non-destructive incident. Analyze why a healthy API can still fail during mission execution, identify the root cause, propose a safe fix, recommend regression tests, and stop before any destructive action."
);
await page.getByLabel("AI provider").selectOption("demo");
await page.screenshot({ path: `${outDir}/02-create-mission.png`, fullPage: true });

await Promise.all([
  page.waitForURL(/\/missions\//, { timeout: 30_000 }),
  page.getByRole("button", { name: /launch mission/i }).click(),
]);
await page.screenshot({ path: `${outDir}/03-execution-progress.png`, fullPage: true });

for (let attempt = 1; attempt <= 45; attempt += 1) {
  const text = await page.locator("body").innerText();
  if (/Mission completed|Waiting for approval|AI analysis report/i.test(text) && !/Initialising/i.test(text)) break;
  await page.waitForTimeout(2_000);
  await page.reload({ waitUntil: "domcontentloaded" });
}

await page.screenshot({ path: `${outDir}/04-analysis-report.png`, fullPage: true });
await browser.close();
