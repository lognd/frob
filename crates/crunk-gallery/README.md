# crunk-gallery

The opt-in gallery of crunk (`cargo install crunk --features gallery`): manifest v1 to v3 with
shipped JSON Schemas (`docs/schemas/crunk-gallery-manifest-v*.json`), cell enumeration over the
spec's `[[platform]]` and `[[screen]]`, GALLERY001 to GALLERY005 and the `gallery check` report
(`crunk-gallery-check-v1.json`). Rendering goes through `gob-exec`; `triage` is a blocking loopback contact sheet with keyboard
verdicts saved to the manifest (no async runtime, so no `tokio`).

## Rendering

`render::render` turns cells into hashed PNGs. `web` platforms run Playwright out of process
(`node/render.mjs`, through `gob-exec`: timeout, env allowlist, output cap); `command` platforms run
their own capture command and write the PNG to `$CRUNK_OUTPUT`. Playwright executes project code, so
a trust notice accompanies every web render. A missing Playwright is a typed error naming
`npm install --save-dev playwright && npx playwright install chromium` (exit code 2).

## T3 accessibility (axe-core)

`a11y::check_a11y` scans one cell with an `a11y::AxeScanner` and returns one `AxeFinding` per violating
node, carrying the axe rule id, the node selector (frames and shadow roots joined with ` >> `), the
HTML snippet and a severity from axe's impact (`critical` and `serious` are errors, the rest warnings).
`a11y::PlaywrightAxe` is the real scanner: the render script in axe mode, through `gob-exec`, with
axe-core resolved from the project (`npm install --save-dev axe-core`). An unreadable report is an
error, never a clean scan; a non-web platform is `A11yError::NotWeb`.
