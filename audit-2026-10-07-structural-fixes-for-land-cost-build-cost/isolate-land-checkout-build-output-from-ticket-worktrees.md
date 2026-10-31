+++
id = "01M6812E1C7E0EFX0G26DH06AQ"
title = "Isolate land-checkout build output from ticket worktrees: dedicated warm target so stale shared-target artifacts stop causing TOOL001 and the manual pre-land clean"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-31T03:46:50Z"
updated = "2026-10-31T04:17:22Z"
idempotency_key = "land-fast-2"
scope = ["crates/frob-worktree/src/work.rs", "crates/frob-land/src/ratchet.rs", "crates/frob-worktree/src/gc/pass.rs", "crates/frob-worktree/src/gc/config.rs", "docs/reference/config.md", "docs/schemas/config.json", "crates/frob-land/src/land.rs", "crates/frob-land/src/train_check.rs", "crates/frob-worktree/tests/work.rs"]

[[acceptance]]
text = "The land checkout builds in its own CARGO_TARGET_DIR, never the dir ticket worktrees write to"
bound = true

[[acceptance]]
text = "Test: concurrent ticket worktree builds do not change land-checkout fingerprints, and no pre-land cargo clean is needed"
bound = true
+++

Root cause of repeated land failures: leakage across worktrees in land-target (E0004 from Lang::C of another ticket). A warm incremental target for land only makes re-checks proportional to the delta.
