+++
id = "01M4MGNX1RJNX032GWZ1NN2YCK"
title = "frob check file-rules cache hit rate is 23 percent (3157 of 13557 files) in the telemetry; find why the cache misses and make worktrees and unchanged files hit"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:39:06Z"
updated = "2026-10-11T04:34:36Z"
scope = ["crates/gob-cache/**", "crates/frob-obligations/src/tickets.rs", "crates/frob-obligations/src/lib.rs"]

[[acceptance]]
text = "the default cache engine fingerprint does not change when the executable's bytes change (so rebuilds and worktrees of one commit share rows), and does when FROB_CACHE_EXE_IDENTITY opts in; measured: file-rule rows no longer fork per build"
bound = true
+++

measured from .frob/telemetry.jsonl: last run files 13557 cached_hits 3157. Suspect the cache key includes the worktree path or the cache dir is per worktree.
