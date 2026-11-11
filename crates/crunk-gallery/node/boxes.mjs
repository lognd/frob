// Captures per-data-id bounding boxes of one gallery cell with Playwright, in the layout-solve
// document shape. Run by crunk-gallery through gob-exec (same runner, timeout and environment as
// render.mjs):   node boxes.mjs <request.json>
// The request is the cell's resolved web platform (built by the same Rust code as a render) plus
// `boxes_output` (where the JSON goes) and `ids` (data-ids to capture; empty means every one).
// Playwright is resolved from the project (cwd), never bundled here.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const GRID = 64;
const request = JSON.parse(readFileSync(process.argv[2], "utf8"));
const require = createRequire(join(process.cwd(), "noop.js"));
const playwright = require("playwright");

const snap = (v) => {
  const s = Math.round(v * GRID) / GRID;
  return s === 0 ? 0 : s;
};

// Runs in the page: one node per requested (or every) data-id, plus the ids it could not find.
function measure(wanted) {
  const FOCUSABLE = "a[href],button,input,select,textarea,[tabindex]";
  const all = [...document.querySelectorAll("[data-id]")];
  const ids = wanted.length ? wanted : all.map((e) => e.getAttribute("data-id"));
  const nodes = [];
  const missing = [];
  for (const id of ids) {
    const el = all.find((e) => e.getAttribute("data-id") === id);
    if (!el) {
      missing.push(id);
      continue;
    }
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const hidden = style.display === "none" || el.getClientRects().length === 0;
    const owner = el.parentElement?.closest("[data-id]");
    const onlyText = el.children.length === 0 && el.textContent.trim() !== "";
    nodes.push({
      id,
      parent: owner ? owner.getAttribute("data-id") : null,
      kind: onlyText ? "text" : "box",
      x: hidden ? 0 : rect.x + window.scrollX,
      y: hidden ? 0 : rect.y + window.scrollY,
      width: hidden ? 0 : rect.width,
      height: hidden ? 0 : rect.height,
      hidden,
      focusable: el.matches(FOCUSABLE) && el.tabIndex >= 0 && !hidden,
    });
  }
  return { nodes, missing };
}

const browser = await playwright[request.engine].launch();
try {
  const context = await browser.newContext({
    viewport: request.viewport,
    deviceScaleFactor: request.device_scale,
    locale: request.locale ?? undefined,
    javaScriptEnabled: request.java_script_enabled,
    colorScheme: request.media.color_scheme,
    reducedMotion: "reduce",
  });
  for (const script of request.init_scripts) await context.addInitScript(script);
  const page = await context.newPage();
  // Settling: fixed clock, animations off, network idle, fonts ready. Anything else is refused.
  if (page.clock?.install) await page.clock.install({ time: 0 });
  await page.goto(request.url, { waitUntil: "networkidle" });
  await page.addStyleTag({
    content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
  });
  if (request.settle_ms > 0) await page.waitForTimeout(request.settle_ms);
  const settled = await page.evaluate(async () => {
    await document.fonts.ready;
    return {
      fonts: document.fonts.status === "loaded",
      animations: document.getAnimations().filter((a) => a.playState === "running").length,
    };
  });
  if (!settled.fonts) throw new Error("unsettled: fonts are not ready");
  if (settled.animations > 0) throw new Error(`unsettled: ${settled.animations} animations still running`);
  const { nodes, missing } = await page.evaluate(measure, request.ids);
  const doc = {
    version: 1,
    viewport_width: request.viewport.width,
    viewport_height: request.viewport.height,
    nodes: nodes.map(({ focusable, ...n }) => ({
      ...n,
      x: snap(n.x),
      y: snap(n.y),
      width: snap(n.width),
      height: snap(n.height),
      ...(n.hidden ? {} : { hidden: undefined }),
    })),
    focus_order: nodes.filter((n) => n.focusable).map((n) => n.id),
    missing,
  };
  writeFileSync(request.boxes_output, JSON.stringify(doc));
} finally {
  await browser.close();
}
