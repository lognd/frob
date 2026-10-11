+++
id = "01M4MNBNM0WGTXGH93PEV48F78"
title = "Normalize source mtimes on worktree and land-checkout creation so shared-target builds compile zero workspace crates"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-11T05:00:53Z"
updated = "2026-10-11T15:56:22Z"
scope = ["crates/frob-worktree/src/work.rs", "crates/frob-land/src/ratchet.rs"]

[[acceptance]]
text = "in a worktree created after a build of the same commit, cargo build of an already built package reports zero Compiling lines, covered by a test"
bound = false

[[acceptance]]
text = "a file edited in the worktree is still rebuilt (mtime newer than the build), covered by a test"
bound = false
+++

Found by ~83RPV1W. Cargo freshness is mtime based: a worktree created after the last build has newer source mtimes than the shared target's dep-info, so every workspace crate is Dirty (measured: gob-time, gob-fs, gob-cache recompile in a same-commit worktree created later; zero when the worktree predates the build or mtimes are set old). sccache does NOT fix it: workspace crate compiles key on the absolute source path, so a second worktree path missed 3 of 3 (0 hits). Fix: after git checkout in frob work and the land base checkout, set the mtime of every tracked file that is unchanged from the base tip to the tip commit time (older than any build of that tip) and leave changed files at now. Test: a file untouched since base keeps mtime <= commit time; an edited file is newer.
