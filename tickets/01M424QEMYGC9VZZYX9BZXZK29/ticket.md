+++
id = "01M424QEMYGC9VZZYX9BZXZK29"
title = "Automatic garbage collection: throttled pass in work and land keeps build output, worktrees, caches and artifacts under budget"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-04T00:23:54Z"
updated = "2026-10-04T01:55:57Z"
scope = ["crates/frob-worktree/**", "crates/frob-land/src/land.rs", "crates/frob/src/doctor_cmd.rs", "crates/gob-config/**", "docs/design/architecture.md", "docs/design/tickets.md", "docs/reference/config.md", "docs/schemas/config.json", "crates/frob/src/doctor.rs", "crates/frob/src/config.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/snapshots/cli__doctor_schema.snap", "crates/frob/tests/snapshots/cli__doctor_fresh_repo.snap", "crates/frob/tests/snapshots/cli__init_frob_toml.snap", "frob.toml", "docs/reference/cli/frob.md", "Cargo.lock", "crates/frob/tests/gc.rs", "crates/frob-land/tests/land.rs"]

[[acceptance]]
text = "Given a target dir over its budget with old and recent artifacts, when a GC pass runs, then old artifacts are evicted until under budget and the latest build's artifacts and the frob and grimble binaries remain"
bound = false

[[acceptance]]
text = "Given a worktree whose ticket is closed but which has uncommitted changes, when a GC pass runs, then it is kept and reported"
bound = false

[[acceptance]]
text = "Given a pass ran within the interval, when frob work runs again, then no pass runs; and given free space below the guard, then a pass runs regardless"
bound = false

[[acceptance]]
text = "Given frob doctor, when it runs, then it shows the last pass, bytes reclaimed and usage per category"
bound = false
+++

Owner request 2026-10-03: garbage collection must be automatic so stale data never builds up again (today the primary checkout's target/ held 127 GB, 74 GB of it build artifacts untouched for over 6 hours plus 28 GB of incremental state; ~107 GB were freed by hand). No new verb unless it is the best way. frob owns local state and the build output of the checkouts it manages; goway owns its remote hosts (its own gc).

Design (document it in architecture.md storage section and tickets.md worktree section):
1. Trigger, no new verb: an opportunistic, throttled GC pass runs inside frob verbs that already run often and are about to need disk: frob work (before a new worktree builds) and frob land (after a worktree is removed), plus frob doctor --fix runs it unthrottled and reports. Throttle with a stamp under the git common dir (at most once per [gc] interval, default 1 h); the pass is bounded in time and never blocks the verb's result (errors are warnings). The disk guard (free space below its threshold) forces an unthrottled pass before refusing work.
2. What is collected, each with a budget or age in [gc] config (defaults on):
   - frob-owned: worktrees whose ticket is closed or whose lease expired with no uncommitted changes (never one with uncommitted work: report it instead); .frob/ caches by least-recent use over a size budget; .git/frob/artifacts evidence blobs older than a retention that no open ticket references.
   - build output of the primary checkout and live worktrees, through a per-ecosystem adapter (Cargo first): remove incremental directories not used within an age (default 6 h), and evict build artifacts by least-recent modification until the target dir is under a per-checkout budget (default 30 GB), never touching the artifacts of the most recent build (keep anything newer than the last successful build's start) and never the frob and grimble binaries.
3. Report: frob doctor shows last pass time, bytes reclaimed, and current usage per category; each pass logs a summary at info.
4. Tests on fixture directories with fake artifacts and controlled mtimes: budgets respected, recent artifacts kept, a worktree with uncommitted changes never removed, throttle honored, guard forces a pass.
