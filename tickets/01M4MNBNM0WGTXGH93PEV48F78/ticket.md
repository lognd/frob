+++
id = "01M4MNBNM0WGTXGH93PEV48F78"
title = "Normalize source mtimes on worktree and land-checkout creation so shared-target builds compile zero workspace crates"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-11T05:00:53Z"
updated = "2026-10-11T16:28:46Z"
scope = ["crates/frob-worktree/src/work.rs", "crates/frob-land/src/ratchet.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/tests/work.rs"]

[[acceptance]]
text = "a worktree created after the tip commit leaves unchanged tracked files with mtime <= the tip commit time (so cargo sees them fresh against any build of that tip), covered by a test"
bound = true

[[acceptance]]
text = "a file edited in the worktree after creation has mtime newer than the tip commit time, so it is still rebuilt, covered by a test"
bound = true
+++

Found by ~83RPV1W. Cargo freshness is mtime based: a worktree created after the last build has newer source mtimes than the shared target's dep-info, so every workspace crate is Dirty (measured: gob-time, gob-fs, gob-cache recompile in a same-commit worktree created later; zero when the worktree predates the build or mtimes are set old). sccache does NOT fix it: workspace crate compiles key on the absolute source path, so a second worktree path missed 3 of 3 (0 hits). Fix: after git checkout in frob work and the land base checkout, set the mtime of every tracked file that is unchanged from the base tip to the tip commit time (older than any build of that tip) and leave changed files at now. Test: a file untouched since base keeps mtime <= commit time; an edited file is newer.
