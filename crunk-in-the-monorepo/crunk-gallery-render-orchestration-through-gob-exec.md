+++
id = "01M43ATDR7DWY5RZPB3QB3GE3K"
title = "crunk-gallery: render orchestration through gob-exec (playwright and command renderers)"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:37Z"
updated = "2026-10-21T08:19:47Z"
idempotency_key = "crunk-plan-gal2"
labels = ["area:crunk"]
scope = ["crates/crunk-gallery/src/render/**", "crates/crunk-gallery/node/**", "crates/crunk-gallery/tests/render*.rs", "crates/crunk-gallery/src/render/mod.rs", "crates/crunk-gallery/src/render/command.rs", "crates/crunk-gallery/src/render/playwright.rs", "crates/crunk-gallery/node/render.mjs", "crates/crunk-gallery/tests/render.rs", "crates/crunk-gallery/src/lib.rs", "crates/crunk-gallery/Cargo.toml", "Cargo.lock", "changelog.d/01M43ATDR7DWY5RZPB3QB3GE3K.added.md", "crates/crunk-gallery/README.md"]

[[links]]
kind = "blocked-by"
target = "01M40VH6HES1X3P57WZS0S9G93"

[[links]]
kind = "blocked-by"
target = "01M43ATDG0RG5DP9PVFAKETJJH"

[[acceptance]]
text = "Given playwright installed, when `crunk gallery render` runs on the fixture, then hashed PNGs are written to the artifacts dir"
bound = true

[[acceptance]]
text = "Given playwright missing, when render runs, then the error names the install command and exits 2"
bound = true

[[acceptance]]
text = "Given a command renderer that hangs, when render runs, then it is killed at the timeout and the cell is marked failed"
bound = true
+++

Port render, renderer, screenshot, web_steps and _playwright (about 1.5k LOC): playwright stays out of process through gob-exec (timeout, env allowlist, output caps; it executes project code, so the trust notice applies), PNGs hashed, the `command` renderer for external capture tools. Missing playwright is a typed error with the remedy. Tests needing playwright run in the optional CI job. v1 T-0225 (capture_attrs) and T-0264 are decided at import, not here.
