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

## Route discovery (GALLERY005)

`router::parse_routes` reads the route paths a `router.tsx` declares: route objects
(`createBrowserRouter([{ path, children }])`) and JSX (`<Route path>`), with nesting joined onto the
parent path. Dynamic segments (`:id`, `:id?`, `/files/*`) are kept verbatim, so a `[[screen]]` covers
them by using the same string as its `entry`; the top-level `*` catch-all needs no screen. A `path`
that is not a string literal (an identifier, a template with `${}`) is a typed
`RouterError::UnsupportedPath` with its line, and a source with no routes is `RouterError::NoRoutes`.
On the CLI, `crunk gallery check --router src/router.tsx` feeds those routes to GALLERY005; the
repeatable `--route` still works and is combined with `--router`.

## T3 accessibility (axe-core)

`a11y::check_a11y` scans one cell with an `a11y::AxeScanner` and returns one `AxeFinding` per violating
node, carrying the axe rule id, the node selector (frames and shadow roots joined with ` >> `), the
HTML snippet and a severity from axe's impact (`critical` and `serious` are errors, the rest warnings).
`a11y::PlaywrightAxe` is the real scanner: the render script in axe mode, through `gob-exec`, with
axe-core resolved from the project (`npm install --save-dev axe-core`). An unreadable report is an
error, never a clean scan; a non-web platform is `A11yError::NotWeb`.

## Reconstruction status

The Python crunk gallery source was not available when this crate was ported, so the manifest v1-v3
shapes and the cell enumeration order were reconstructed from notes and fixtures. They have not been
diffed against Python. `tests/it/golden.rs` and `tests/golden/screens_v1_1.cells.txt` pin the current
behaviour so drift is caught, but they prove no parity with the Python gallery.
