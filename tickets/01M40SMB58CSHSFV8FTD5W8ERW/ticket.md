+++
id = "01M40SMB58CSHSFV8FTD5W8ERW"
title = "cycle close before the end date truncates the window to the close date"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:50:43Z"
updated = "2026-10-03T12:24:19Z"
idempotency_key = "m2-rel-cycle-early-close"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/**", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs", "changelog.d/01M40SMB58CSHSFV8FTD5W8ERW.fixed.md", "docs/design/pm-enforcement.md"]

[[acceptance]]
text = "Given a 7-day cycle closed on its first day, when a new cycle starting the next day is created, then it is accepted"
bound = true

[[acceptance]]
text = "Given a cycle closed early, when velocity or the ratio is computed, then only done events up to the close day count"
bound = true
+++

Owner preference 2026-10-03: many 1-3 day cycles, closed early as soon as their goal is met. Today a cycle closed early keeps its planned end date, so (1) a new cycle starting the next day is refused as overlapping, and (2) velocity counts done work in the old window too (double counting). Fix: closing before the planned end records the effective end (the close day) as the cycle's end; the overlap check, velocity, capacity and the commitment ratio use the effective window; show and list display planned and effective ends. Also allow closing a cycle whose members are all done or carried without --carry-to when nothing needs carrying (already true) and make the remedy for E-CYCLE-NO-NEXT suggest a cycle starting the day after the effective end. Set [pm] cycle_days = 2 in this repository's frob.toml.
