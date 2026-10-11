+++
id = "01M4MGNX1RJNX032GWZ1NN2YCK"
title = "frob check file-rules cache hit rate is 23 percent (3157 of 13557 files) in the telemetry; find why the cache misses and make worktrees and unchanged files hit"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:39:06Z"
updated = "2026-10-11T03:52:48Z"
scope = ["crates/gob-cache/**"]

[[acceptance]]
text = "on a second frob check with no changed files the cached_hits equals the file count, and across a new worktree of the same commit it is above 90 percent, covered by a test"
bound = false
+++

measured from .frob/telemetry.jsonl: last run files 13557 cached_hits 3157. Suspect the cache key includes the worktree path or the cache dir is per worktree.
