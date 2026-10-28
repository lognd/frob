+++
id = "01M61M9EC18DSB04FSVMTBE4QF"
title = "Burn down COH002/COH003/ERR001-3/MDL008/CI004/CI005/CAP001/PM012/PM032/PARSE002 findings and re-enable the rules"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-28T16:08:01Z"
updated = "2026-10-28T16:08:01Z"
scope = ["crates/**", "design/**", ".github/**", "scripts/**", "frob.toml"]

[[acceptance]]
text = "Each rule has zero findings or a baseline entry, and its [rules.<ID>] severity=off table is deleted from frob.toml"
bound = false
+++

Found while working ~1G4B9C1: collapsing Severity made these former Warn/Advisory rules Errors; they are set off in frob.toml until burned down (see rules.md 6.1.7). Counts at the time: COH003 2360, ERR002 388, COH002 129, MDL008 24, ERR001 13, PM012 13, CI004 3, CI005 3, CAP001 1, ERR003 1, PARSE002 1, PM032 1.
