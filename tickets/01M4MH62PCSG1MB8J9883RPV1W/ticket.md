+++
id = "01M4MH62PCSG1MB8J9883RPV1W"
title = "Shared build cache for ticket worktrees: sccache or a content-addressed rlib store so a new worktree does not rebuild the workspace and land checkouts start warm"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:56Z"
updated = "2026-10-14T20:51:18Z"
scope = ["frob.toml"]

[[links]]
kind = "blocked-by"
target = "01M4MNBNM0WGTXGH93PEV48F78"

[[acceptance]]
text = "the second ticket worktree built on the same commit compiles zero workspace crates, measured from cargo build timings, and the land checkout reuses the same cache"
bound = false
+++

measured: land checkouts are cold, which is why frob.toml carries a 1200 s timeout for cargo stages, and shared target directories gave stale-artifact compile errors (E-LAND-CHECK-RED) several times in this session.
