+++
id = "01M4069SYRHMYXCFAZH0AN408B"
title = "frob cycle velocity from done events"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:55Z"
updated = "2026-10-03T14:54:29Z"
idempotency_key = "m2-rel-cycle-velocity"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/cycle/velocity.rs", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs", "docs/reference/cli/frob.md", "crates/frob-pm/src/cycle/lifecycle.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069RPPQE1ES1914K6V6Y0D"

[[acceptance]]
text = "Given three closed cycles with known done points, when velocity runs, then the mean and standard deviation match"
bound = true

[[acceptance]]
text = "Given fewer than min_history cycles, when velocity runs, then no capacity is derived and the sample count is shown"
bound = true
+++

Points of story, task, bug and chore tickets with points that reached done inside each cycle window (carry-over counted in the completing cycle only); prints the last N cycles, rolling mean and standard deviation; below min_history it prints the samples and no capacity.
