+++
id = "01M69111N328P45MG4C0NTRDJF"
title = "crunk cache prune: --age N (delete entries older than N days)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-31T13:05:18Z"
updated = "2026-11-17T04:32:32Z"
labels = ["no-story", "good-first"]
scope = ["crates/crunk/src/cache.rs", "crates/gob-cache/src/lib.rs", "crates/crunk/tests/**", "crates/crunk/tests/e2e/divergences.toml"]

[[acceptance]]
text = "Given cache rows older than N days, when crunk cache prune --age N runs, then those rows are deleted and it exits 0"
bound = false

[[acceptance]]
text = "Given the e2e_57 step 6 cache prune --age 0, when the e2e runs, then the cache-verb-removed divergence is gone"
bound = false
+++

found while working ~Z03B67Y: e2e_57 step 6 (cache prune --age 0) still exits 2.

## Start here

- Files to read first: crates/crunk/src/cache.rs (the prune verb) and crates/gob-cache/src/lib.rs (row deletion)
- Test command: cargo nextest run -p crunk -p gob-cache
- Who to ask: lognd
