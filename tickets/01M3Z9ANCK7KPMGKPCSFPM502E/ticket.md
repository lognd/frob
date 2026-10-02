+++
id = "01M3Z9ANCK7KPMGKPCSFPM502E"
title = "gob-dev and gob-mdtest locate the repository through compile-time CARGO_MANIFEST_DIR"
type = "bug"
category = "todo"
priority = "critical"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:46:34Z"
updated = "2026-10-02T21:46:34Z"
idempotency_key = "m2-manifest-dir"
labels = ["milestone:2"]
scope = ["crates/gob-dev/**", "crates/gob-mdtest/**"]

[[acceptance]]
text = "Given gob-dev compiled in one worktree and run from another, when cargo dev gen all --check runs, then it compares against the current worktree's files and exits 0 on a clean tree"
bound = false
+++

crates/gob-dev/src/lib.rs:86 resolves the workspace root as env!(CARGO_MANIFEST_DIR)/../.. at compile time. With the shared build directory every worktree uses (/home/logan/projects/frob-v2-wt/.target), a cached gob-dev binary keeps the path of the worktree it was compiled in; once that worktree is removed, cargo dev gen all --check reports all 44 generated files missing and the GEN001 tool stage fails every land. gob-mdtest has the same pattern. Resolve the root at run time: --root flag, else walk up from the current directory to the Cargo.toml containing [workspace]; mdtest corpora resolve relative to the runtime CARGO_MANIFEST_DIR env var that cargo sets when running tests, not the compile-time one.
