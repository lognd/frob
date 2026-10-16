+++
id = "01M43ATD7ZGTNCY5036AYEJR7P"
title = "crunk preview, diff and init with presets and detection"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:37Z"
updated = "2026-10-16T01:18:00Z"
idempotency_key = "crunk-plan-prev"
labels = ["area:crunk"]
scope = ["crates/crunk/src/preview.rs", "crates/crunk/src/diff.rs", "crates/crunk/src/init/**", "crates/crunk/tests/init*.rs", "crates/crunk/src/lib.rs", "crates/crunk/Cargo.toml", "crates/gob-product/src/product.rs", "crates/gob-product/src/workspace.rs", "docs/crunk", "changelog.d", "crates/gob-dev/profile.toml", "docs/crunk/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARX764095Q4VWABWXXV5H"

[[links]]
kind = "blocked-by"
target = "01M43ARZH9F9MCPJCKXM635E0X"

[[links]]
kind = "blocked-by"
target = "01M43ATCF5GGK59S96K1ZF0G9C"

[[acceptance]]
text = "Given an empty Vite project, when `crunk init` runs, then the files are written and `crunk check` on the result exits 0"
bound = true

[[acceptance]]
text = "Given NO_COLOR set, when preview runs, then no escape codes are printed"
bound = true

[[acceptance]]
text = "Given two spec dirs, when `crunk diff` runs, then added, removed and changed tokens are listed"
bound = true
+++

Port report/preview_out.py (ANSI truecolor sheet, NO_COLOR aware), `diff OTHER` token-set diff, and scaffold/ (588 LOC: init --preset default|mono, --force, detect [jsx]/[tailwind], writes crunk.toml, bucket dirs, reset.css, tokens). The scaffold must pass its own check (FROBLEMS item 8). Port tests/unit/test_scaffold.py, test_report_preview.py, e2e 01, INT-08.
