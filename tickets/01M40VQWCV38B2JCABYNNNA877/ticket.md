+++
id = "01M40VQWCV38B2JCABYNNNA877"
title = "cycle close early with unfinished work deadlocks: the next cycle cannot exist yet"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T12:27:36Z"
updated = "2026-10-03T13:15:31Z"
idempotency_key = "m2-rel-close-creates-next"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/**", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs", "docs/design/pm-enforcement.md", "changelog.d/01M40VQWCV38B2JCABYNNNA877.fixed.md"]

[[acceptance]]
text = "Given an open 7-day cycle on its first day with unfinished members, when cycle close with --next-goal runs, then a next cycle starting tomorrow exists, the members are carried into it, and the ratio counts them as committed"
bound = true

[[acceptance]]
text = "Given the same without --next-goal, when close runs, then it refuses with a remedy naming --next-goal"
bound = false
+++

Found while switching this repository to 2-day cycles (owner: close early when the goal is met): closing a cycle before its planned end with incomplete members needs a carry target, but creating the next cycle (starting the day after today) is refused as overlapping the still-open cycle's planned window; the only workaround (unassigning incomplete members first) records a false commitment ratio. Fix: cycle close CYCLE --next-goal TEXT [--next-days N] creates the next cycle starting the day after the effective end (cycle_days long unless --next-days), in the same operation, and carries the incomplete members into it; the overlap check for that creation uses the effective end being recorded. E-CYCLE-NO-NEXT's remedy names --next-goal. Tests: early close with unfinished work and --next-goal creates the next cycle, carries members and records the true ratio; without --next-goal the remedy names it.
