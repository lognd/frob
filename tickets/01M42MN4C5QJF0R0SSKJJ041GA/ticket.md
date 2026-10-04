+++
id = "01M42MN4C5QJF0R0SSKJJ041GA"
title = "shared_dir returns differently spelled paths for primary and linked worktrees on Windows (8.3 short name vs long name)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 1
reporter = "lognd"
created = "2026-10-04T05:02:15Z"
updated = "2026-10-04T05:02:27Z"
scope = ["crates/gob-cache/src/lib.rs", "crates/gob-cache/tests/shared.rs"]

[[acceptance]]
text = "Given a primary checkout and a linked worktree, when shared_dir runs for each on Windows, then both return the identical canonical path"
bound = false
+++

CI run 37177956559 (windows-latest): gob-cache::shared primary_and_linked_worktree_share_one_cache_dir fails: primary resolves to C:\Users\RUNNER~1\... (8.3 short name from the temp dir) while the linked worktree resolves through its gitdir to C:\Users\runneradmin\... . Both name the same directory but the strings differ, so anything keyed or compared by the path disagrees. shared_dir and git_common_dir must return gob_exec::canonical forms on every branch (paths.md section 3.1).
