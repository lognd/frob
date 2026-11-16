+++
id = "01M7JRZXJX15DREGFWA9ND1FQW"
title = "gob-dev gen all --check: confirm it fails on a stale crate map and investigate slowness"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-16T18:12:59Z"
updated = "2026-11-16T18:12:59Z"
labels = ["no-story"]
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "Given a stale docs/reference/crates.md, when gob-dev gen all --check runs, then it exits non-zero naming the file"
bound = false
+++

The 7BCYC26 implementer run of gen all --check timed out at 590s so the stale-map failure is unconfirmed. Measure and speed up. no-story: internal tooling.
