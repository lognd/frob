// Tailwind truth helper (T-0208): runs INSIDE the target project's own node
// and node_modules -- never crunk's. Ships no npm dependencies of its own;
// it only calls into whatever `tailwindcss` (v3) or `@tailwindcss/node` (v4)
// the target project already has installed.
//
// Invocation contract (see crunk_tailwind::runtime): argv[2] is the
// path to a request JSON file, one of:
//   {"mode": "v3", "projectRoot": "...", "configPath": "...", "candidates": [...]}
//   {"mode": "v4", "projectRoot": "...", "cssEntryPath": "...", "candidates": [...]}
//   {"mode": "v3-theme", "projectRoot": "...", "configPath": "..."}
//   {"mode": "v4-theme", "projectRoot": "...", "cssEntryPath": "..."}
// A single JSON object is written to stdout: {"ok": true, "css": "...",
// "version": "v3"|"v4", "configPath": "..."} (candidate modes) or
// {"ok": true, "theme": {"name": "value", ...}, "version": "v3"|"v4",
// "configPath": "..."} (theme modes) or {"ok": false, "error": "..."}.
// Crashes (bad request, missing module) still try to emit an {"ok": false}
// object so the Rust side never has to guess at a bare non-zero exit.
//
// The theme modes (T-0211) resolve the PROJECT-OWNED subset of Tailwind's
// fully-merged theme (defaults + presets + plugins + `theme.extend`/
// `@theme`): each computes the project's own resolved theme, diffs it
// against Tailwind's PURE default theme (no user config at all) by fully
// flattened dotted path, and keeps only entries that differ or are new --
// Tailwind's own built-in color/spacing/etc. scale never appears, only
// what the project itself contributed (matching what TW00x needs to judge
// a class as "project-owned" per crunk-testbed's own tailwind.config.js
// comment). A value this can't reduce to a plain string (an unresolvable
// function call, a non-string leaf) is left out, never guessed.

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

/** Read and JSON-parse the request file named on argv[2]. */
function readRequest() {
  const requestPath = process.argv[2];
  if (!requestPath) {
    throw new Error("usage: helper.mjs <request.json>");
  }
  return JSON.parse(fs.readFileSync(requestPath, "utf8"));
}

/** Emit the final JSON response on stdout and exit 0 (errors are in-band). */
function emit(response) {
  process.stdout.write(JSON.stringify(response));
}

/** Tailwind v3's base config for BOTH the candidate and theme paths
 * (T-0210): no configured file means Tailwind's own default config (an
 * empty user config resolves to the pure defaults via resolveConfig),
 * never a hard failure -- `configPath` in the response is then `null`.
 * ONE shared decision so runV3/runV3Theme can never diverge on it again.
 */
function loadV3BaseConfig(request, require) {
  if (!request.configPath) {
    return { configPath: null, baseConfig: {} };
  }
  const loadConfig = require("tailwindcss/loadConfig");
  const configPath = path.resolve(request.configPath);
  return { configPath, baseConfig: loadConfig(configPath) };
}

/** Tailwind v3: loadV3BaseConfig + postcss+tailwindcss with `content`
 * narrowed to exactly the candidate strings (no filesystem scan), which
 * is Tailwind's own documented `{raw: ...}` content source.
 */
async function runV3(request) {
  const require = createRequire(path.join(request.projectRoot, "package.json"));
  const postcss = require("postcss");
  const tailwindcss = require("tailwindcss");

  const { configPath, baseConfig } = loadV3BaseConfig(request, require);
  const candidateConfig = {
    ...baseConfig,
    content: [{ raw: request.candidates.join(" "), extension: "html" }],
  };

  const result = await postcss([tailwindcss({ config: candidateConfig })]).process(
    "@tailwind utilities;",
    { from: undefined },
  );
  return { ok: true, version: "v3", configPath, css: result.css };
}

/** Tailwind v4: `@tailwindcss/node`'s `compile(css, opts).build(candidates)`,
 * per the OWNER DECISION architecture -- the project's own CSS entry (which
 * carries `@import "tailwindcss"` and any `@config`/`@theme`) is compiled
 * once, then built against exactly the candidate set.
 */
async function runV4(request) {
  const require = createRequire(path.join(request.projectRoot, "package.json"));
  const { compile } = require("@tailwindcss/node");

  const cssEntryPath = path.resolve(request.cssEntryPath);
  const css = fs.readFileSync(cssEntryPath, "utf8");
  const base = path.dirname(cssEntryPath);

  const compiled = await compile(css, { base, onDependency: () => {} });
  const built = compiled.build(request.candidates);
  return { ok: true, version: "v4", configPath: cssEntryPath, css: built };
}

/** Call `value` if it is a Tailwind theme function (color opacity helpers
 * etc), with a fixed `opacityValue` so the result is a concrete string
 * rather than a function reference; a throwing/non-string-returning
 * function resolves to `undefined` (unresolved, never guessed).
 */
function callIfFunction(value) {
  if (typeof value !== "function") return value;
  try {
    const result = value({ opacityValue: "1" });
    return typeof result === "string" ? result : undefined;
  } catch {
    return undefined;
  }
}

/** Flatten a Tailwind v3 theme object into `out` (a `Map<dottedPath,
 * string>`), namespace-transparent (no key is ever the flattened path's
 * own name -- see helper.mjs's module docstring): a string leaf is kept
 * as-is, a plain string array (e.g. `fontFamily`) is joined with `, `, a
 * Tailwind `[value, {lineHeight: ...}]` fontSize-style tuple keeps only
 * its leading string, and anything else (a number, a function that did
 * not reduce to a string, an empty/mixed array) is left out.
 */
function flattenV3Theme(node, pathParts, out) {
  const value = callIfFunction(node);
  if (value === undefined || value === null) return;
  if (Array.isArray(value)) {
    if (value.length > 0 && value.every((item) => typeof item === "string")) {
      out.set(pathParts.join("."), value.join(", "));
      return;
    }
    if (value.length > 0 && typeof value[0] === "string") {
      out.set(pathParts.join("."), value[0]);
    }
    return;
  }
  if (typeof value === "object") {
    for (const [key, sub] of Object.entries(value)) {
      flattenV3Theme(sub, [...pathParts, key], out);
    }
    return;
  }
  if (typeof value === "string") {
    out.set(pathParts.join("."), value);
  }
}

/** Tailwind v3: `resolveConfig` the project's own config (defaults +
 * presets + plugins + `theme.extend`, including anything a plugin/
 * preset/`require()`'d JSON file contributes), diffed against
 * `resolveConfig({})`'s pure defaults, reduced to a `{name: value}` map
 * keyed by each surviving dotted path's LAST segment (matching the shape
 * the static fallback of crunk-ingest already emits).
 */
async function runV3Theme(request) {
  const require = createRequire(path.join(request.projectRoot, "package.json"));
  const resolveConfig = require("tailwindcss/resolveConfig");

  // T-0211/T-0210: `loadV3BaseConfig` is the ONE place this "no config
  // means Tailwind's own defaults" decision lives, shared with runV3.
  const { configPath, baseConfig } = loadV3BaseConfig(request, require);

  const resolved = resolveConfig(baseConfig);
  const pureDefault = resolveConfig({});

  const projectFlat = new Map();
  flattenV3Theme(resolved.theme, [], projectFlat);
  const defaultFlat = new Map();
  flattenV3Theme(pureDefault.theme, [], defaultFlat);

  const theme = {};
  for (const [dottedPath, value] of projectFlat) {
    if (defaultFlat.get(dottedPath) !== value) {
      theme[dottedPath.split(".").pop()] = value;
    }
  }
  return { ok: true, version: "v3", configPath, theme };
}

/** Tailwind v4: `__unstable__loadDesignSystem` the project's own CSS entry
 * (which carries `@import "tailwindcss"` and any `@config`/`@theme`),
 * diffed against a bare `@import "tailwindcss";` design system's own
 * `theme.entries()` by CSS custom-property name, keeping only entries
 * that differ or are new (the project's own contribution) -- then
 * namespace-stripped the same way crunk-ingest's static v4
 * reader already does, in Rust, from the raw `--name` keys returned
 * here.
 */
async function runV4Theme(request) {
  const require = createRequire(path.join(request.projectRoot, "package.json"));
  const { __unstable__loadDesignSystem } = require("@tailwindcss/node");

  const cssEntryPath = path.resolve(request.cssEntryPath);
  const css = fs.readFileSync(cssEntryPath, "utf8");
  const base = path.dirname(cssEntryPath);

  const design = await __unstable__loadDesignSystem(css, { base });
  const baseline = await __unstable__loadDesignSystem('@import "tailwindcss";', {
    base,
  });

  const projectEntries = new Map(design.theme.entries());
  const baselineEntries = new Map(baseline.theme.entries());

  const theme = {};
  for (const [varName, entry] of projectEntries) {
    const baselineEntry = baselineEntries.get(varName);
    if (!baselineEntry || baselineEntry.value !== entry.value) {
      theme[varName] = entry.value;
    }
  }
  return { ok: true, version: "v4", configPath: cssEntryPath, theme };
}

async function main() {
  let request;
  try {
    request = readRequest();
  } catch (err) {
    emit({ ok: false, error: `bad request: ${err.message}` });
    return;
  }

  try {
    if (request.mode === "v3") {
      emit(await runV3(request));
    } else if (request.mode === "v4") {
      emit(await runV4(request));
    } else if (request.mode === "v3-theme") {
      emit(await runV3Theme(request));
    } else if (request.mode === "v4-theme") {
      emit(await runV4Theme(request));
    } else {
      emit({ ok: false, error: `unknown mode: ${request.mode}` });
    }
  } catch (err) {
    emit({ ok: false, error: `${err.name}: ${err.message}` });
  }
}

main();
