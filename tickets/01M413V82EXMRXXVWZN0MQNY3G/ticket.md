+++
id = "01M413V82EXMRXXVWZN0MQNY3G"
title = "A cycle whose start date has come stays planned; state never becomes active"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-03T14:49:15Z"
updated = "2026-10-03T15:14:24Z"
scope = ["crates/frob-pm/src/cycle/**", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs"]

[[acceptance]]
text = "Given a cycle starting today, when cycle show or list runs, then its state is active"
bound = true

[[acceptance]]
text = "Given a cycle starting tomorrow, when shown, then planned; and a closed cycle shows closed regardless of dates"
bound = true
+++

Reported by mdcat (FROB_FEEDBACK item 2), reproduced on experimental 2026-10-03: cycle new --start <today> then cycle list shows state planned all day, also after member tickets were worked and landed. State is a fold over events plus the clock: a cycle is active when today (UTC, injected clock) is within start..effective end and it is not closed; planned before start; closed after close. No activation event is needed.
