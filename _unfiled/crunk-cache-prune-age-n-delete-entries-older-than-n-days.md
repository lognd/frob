+++
id = "01M69111N328P45MG4C0NTRDJF"
title = "crunk cache prune: --age N (delete entries older than N days)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-31T13:05:18Z"
updated = "2026-10-31T13:05:18Z"
scope = ["crates/crunk/src/cache.rs", "crates/gob-cache/src/lib.rs", "crates/crunk/tests/**"]

[[acceptance]]
text = "crunk cache prune --age N deletes rows older than N days and exits 0"
bound = false

[[acceptance]]
text = "the cache-verb-removed e2e divergence is removed"
bound = false
+++

found while working ~Z03B67Y: e2e_57 step 6 (cache prune --age 0) still exits 2.
