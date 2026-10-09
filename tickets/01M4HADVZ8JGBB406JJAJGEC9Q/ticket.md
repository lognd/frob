+++
id = "01M4HADVZ8JGBB406JJAJGEC9Q"
title = "Scoped cargo stages at land: clippy and fmt over affected crates and reverse dependencies (-p)"
type = "task"
category = "todo"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-09T21:52:07Z"
updated = "2026-10-09T21:52:07Z"
scope = ["crates/gob-check/src/tools.rs", "crates/gob-check/src/config.rs", "changelog.d/**"]

[[acceptance]]
text = "Given a ticket touching one crate, when it lands, then clippy and fmt run with -p over that crate and its reverse dependencies only"
bound = false
+++

found while working ~RDRSZC5: that ticket added stage inputs gating only. Remaining: a stage option that appends -p <crate> for each crate owning a scope file plus its reverse dependencies (cargo metadata), needed for the under-60-s land target.
