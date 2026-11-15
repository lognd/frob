+++
id = "01M7EXR0C90EXW6FJF9MPGA3CB"
title = "gen tool stage memoization keys"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:05Z"
updated = "2026-11-15T06:19:05Z"
labels = ["no-story"]

[[acceptance]]
text = "Unchanged inputs skip the gen stage (test)"
bound = false
+++

Source: frob-audit2-repo.md M1/F7. Evidence: frob.toml:47-53, crates/gob-check/src/tools.rs:93-101 cannot memoize the gen stage. Remedy: declare input globs so the stage is skipped on a cache hit. Files: those.
