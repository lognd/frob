+++
id = "01M4069SHBAEWRX9WWCSS2FEHN"
title = "frob cycle assign with capacity and over-commit"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:54Z"
updated = "2026-10-03T11:23:41Z"
idempotency_key = "m2-rel-cycle-assign"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/cycle/assign.rs", "crates/frob/src/cycle_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069RPPQE1ES1914K6V6Y0D"

[[acceptance]]
text = "Given a cycle at capacity, when assign runs without --over-commit, then it exits 3 with the remedy"
bound = false

[[acceptance]]
text = "Given --over-commit --reason, when assign runs, then the event records the reason"
bound = false
+++

`cycle assign TICKET CYCLE` appends a cycle event (op assign); refuses past capacity (capacity_points, or rolling mean minus k*stddev once min_history cycles exist, otherwise unenforced) with exit 3 and remedy `--over-commit --reason`; the reason is recorded as an over-commit event. Needs capacity from velocity but only the set-capacity path is required at first.
