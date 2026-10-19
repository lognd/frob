+++
id = "01M43ATCQVX9A1TJ6A4AE48FDX"
title = "crunk fix: autofix engine on gob-fix (Tier A, tolerance-gated)"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:36Z"
updated = "2026-10-19T04:14:15Z"
idempotency_key = "crunk-plan-afix"
labels = ["area:crunk"]
scope = ["crates/crunk-fix/**", "crates/crunk/src/fix.rs", "crates/crunk/tests/fix*.rs", "Cargo.lock", "crates/crunk/src/lib.rs", "crates/crunk/Cargo.toml", ".gitignore", "changelog.d/01M43ATCQVX9A1TJ6A4AE48FDX.added.md", "docs/reference/grl/catalog.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARX0JB4A8E1YW329MKDDF"

[[links]]
kind = "blocked-by"
target = "01M43ATB4X0B56W8T0G8MQFYVM"

[[links]]
kind = "blocked-by"
target = "01M43ATBDWVSJBXP7TEQ6DBW3W"

[[links]]
kind = "blocked-by"
target = "01M43ATCF5GGK59S96K1ZF0G9C"

[[acceptance]]
text = "Given a machine-applicable fix on a stylesheet finding, when `crunk fix` runs, then the span is rewritten atomically and every byte outside it is untouched (INV-FIX-01 property test)"
bound = true

[[acceptance]]
text = "Given `--dry-run`, when run, then the diff equals the diff of the real run and no file changes"
bound = true

[[acceptance]]
text = "Given a finding with no fix (an out-of-tolerance value) or a non-stylesheet (JSX style-prop) site, when fix runs, then it is left alone"
bound = true
+++

Port crunk.fixes use: rules attach Fix payloads (COLOR001, SPACE001, TYPE001, RADIUS001, SIZE001) as Tier A machine fixes per monorepo.md 3, gated by fix_tolerance and color_tolerance; translucent colors rewrite as color-mix(...); JSX style-prop sites never fixed; `crunk fix [--dry-run]` with dry-run output byte-identical to the real run. INV-FIX-01 (bytes outside edited spans untouched) and INV-FIX-02 (re-check of a fixed site is clean) become property tests. Port tests/unit/test_fixes.py, INT-05, e2e 03.
