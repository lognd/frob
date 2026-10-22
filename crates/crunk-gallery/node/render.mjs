// Renders one gallery cell with Playwright. Run by crunk-gallery through gob-exec:
//   node render.mjs <request.json>
// The request is the cell's resolved web platform plus the state's script; the PNG goes to
// `request.output`, or, when `request.axe_output` is set, axe-core's violations go there as JSON. Playwright is resolved from the project (cwd), never bundled here.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const request = JSON.parse(readFileSync(process.argv[2], "utf8"));
const require = createRequire(join(process.cwd(), "noop.js"));
const playwright = require("playwright");

async function step(page, action) {
  switch (action.kind) {
    case "click":
      return page.click(action.selector);
    case "hover":
      return page.hover(action.selector);
    case "focus":
      return page.focus(action.selector);
    case "fill":
      return page.fill(action.selector, action.value ?? "");
    case "press":
      return page.press(action.selector, action.key);
    case "wait_for":
      return page.waitForSelector(action.selector, { timeout: action.timeout_ms ?? 30000 });
    default:
      throw new Error(`unknown action kind: ${action.kind}`);
  }
}

async function applyNetwork(context, rules) {
  for (const rule of rules) {
    await context.route(rule.url_pattern, async (route) => {
      if (rule.action === "abort") return route.abort();
      if (rule.action === "status") return route.fulfill({ status: rule.status ?? 500, body: "" });
      if (rule.action === "delay") {
        await new Promise((r) => setTimeout(r, rule.delay_ms ?? 0));
        return route.continue();
      }
      return new Promise(() => {}); // hold: never resolves
    });
  }
}

const browser = await playwright[request.engine].launch();
try {
  const context = await browser.newContext({
    viewport: request.viewport,
    deviceScaleFactor: request.device_scale,
    locale: request.locale ?? undefined,
    javaScriptEnabled: request.java_script_enabled,
    colorScheme: request.media.color_scheme,
    reducedMotion: request.media.reduced_motion ? "reduce" : "no-preference",
  });
  for (const script of request.init_scripts) await context.addInitScript(script);
  await applyNetwork(context, request.network);
  const page = await context.newPage();
  if (request.cpu_throttle || request.network_throttle) {
    const cdp = await context.newCDPSession(page);
    if (request.cpu_throttle) await cdp.send("Emulation.setCPUThrottlingRate", { rate: request.cpu_throttle });
    if (request.network_throttle) {
      await cdp.send("Network.emulateNetworkConditions", {
        offline: false,
        downloadThroughput: request.network_throttle.download,
        uploadThroughput: request.network_throttle.upload,
        latency: request.network_throttle.latency,
      });
    }
  }
  await page.goto(request.url, { waitUntil: "networkidle" });
  for (const action of request.actions) await step(page, action);
  if (request.settle_ms > 0) await page.waitForTimeout(request.settle_ms);
  if (request.expect_url && !page.url().includes(request.expect_url)) {
    throw new Error(`expected url ${request.expect_url}, ended on ${page.url()}`);
  }
  if (request.output) await page.screenshot({ path: request.output, fullPage: true });
  if (request.axe_output) {
    // T3: run axe-core (resolved from the project, never bundled here) against the settled page.
    const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
    await page.evaluate(axeSource);
    const results = await page.evaluate(() => axe.run(document));
    writeFileSync(request.axe_output, JSON.stringify({ violations: results.violations }));
  }
} finally {
  await browser.close();
}
