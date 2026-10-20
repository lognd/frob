+++
id = "01M4W7DAHAVC5HDWJJ5NPGXR8M"
title = "Land verification re-runs the whole workspace (clippy, rustdoc, test build) on every land: make it touched-set incremental and offloadable"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-14T03:31:03Z"
updated = "2026-10-14T04:17:41Z"
idempotency_key = "land-check-cost-20261013"
scope = ["crates/frob-land/**", "docs/design/tickets.md"]

[[acceptance]]
text = "A single-crate ticket lands with clippy/doc/test build limited to affected crates; per-stage timings appear in the land envelope; a stale-base retry reuses unaffected stage results; offload to a helper works and falls back locally."
bound = true
+++

Measured 2026-10-13 on a loaded 12-core laptop: a clean land of ~1QXB4AZ took 18 min (2 attempts); the lock holder runs, in sequence, grimble check, cargo test --no-run, fmt, clippy --workspace --all-targets --all-features, cargo doc --workspace, then tests, each over the whole workspace, because the tree digest after merging the moved base always misses the check cache. Fix: (1) scope clippy/doc/test build to the crates affected by the ticket diff plus reverse dependents (the touched-set machinery behind frob test) with a full-workspace run only on a schedule/CI; (2) run land stages on a goway helper (--with-git, --wait) when one is up, falling back to local; (3) reuse stage results across the E-LAND-STALE retry when the merged-in base delta does not touch the stage inputs; (4) print per-stage wall time in the land envelope so slow stages are visible. Related: ~78ATXCB (hang and lock contention).
