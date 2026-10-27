+++
id = "01M4Y2XTH8Q817362APA13CTAJ"
title = "Share one cargo target dir across ticket worktrees and land checkouts (frob-managed CARGO_TARGET_DIR)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T20:51:09Z"
updated = "2026-10-27T02:58:20Z"
scope = ["crates/frob-worktree/**"]
+++

found while working ~83RPV1W. Measured 2026-10-14: sccache 0.18 with CARGO_INCREMENTAL=0 caches registry deps (51 hits) but gets 0 hits for workspace crates when the same commit is built at a second worktree path (12 misses of 12): sccache hashes CARGO_MANIFEST_DIR and cwd, and stable cargo has no trim-paths. So sccache cannot make a second worktree compile zero workspace crates. With source mtimes normalized (~EV48F78, done) a shared CARGO_TARGET_DIR does reuse fingerprints; frob should export one (per toolchain/profile) to worktree and land-checkout cargo stages, or doc a recommended setting. Acceptance of ~83RPV1W moves here.
