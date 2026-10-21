# crunk-gallery

The opt-in gallery of crunk (`cargo install crunk --features gallery`): manifest v1 to v3 with
shipped JSON Schemas (`docs/schemas/crunk-gallery-manifest-v*.json`), cell enumeration over the
spec's `[[platform]]` and `[[screen]]`, GALLERY001 to GALLERY005 and the `gallery check` report
(`crunk-gallery-check-v1.json`). Rendering is separate work.

## Rendering

`render::render` turns cells into hashed PNGs. `web` platforms run Playwright out of process
(`node/render.mjs`, through `gob-exec`: timeout, env allowlist, output cap); `command` platforms run
their own capture command and write the PNG to `$CRUNK_OUTPUT`. Playwright executes project code, so
a trust notice accompanies every web render. A missing Playwright is a typed error naming
`npm install --save-dev playwright && npx playwright install chromium` (exit code 2).
