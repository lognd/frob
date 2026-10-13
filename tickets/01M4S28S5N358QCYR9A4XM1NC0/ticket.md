+++
id = "01M4S28S5N358QCYR9A4XM1NC0"
title = "frob work links a new ticket worktree's target/ to the shared land-target so a second worktree on the same commit compiles zero workspace crates"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-12T22:03:28Z"
updated = "2026-10-13T00:12:01Z"
scope = ["crates/frob-worktree/src/work.rs", "crates/frob-land/src/ratchet.rs", "crates/frob-worktree/tests/work.rs", "crates/frob-worktree/src/gc/config.rs", "docs/reference/config.md", "docs/schemas/config.json"]
+++

found while working ~83RPV1W. Measured 2026-10-12 with a symlinked target to .git/frob/land-target: second worktree with fresh mtimes recompiled 56 workspace crates; after mtime normalization (frob work already does it) 0. So the only missing piece is linking target/ at frob work creation (today only land links it, share_build_dir, and only when target is absent). sccache does not help (path-keyed workspace crates). Keep land-target size-capped via worktree.target_budget_gb.
