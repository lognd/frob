+++
id = "01M3ZX86ZX0SCN2FHTDBQF97FD"
title = "TICK007 misfiled-ticket with machine fix"
type = "task"
category = "todo"
priority = "high"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-03T03:34:46Z"
idempotency_key = "m2-nav-tick007"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-obligations/src/tick_misfiled.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a ticket file at a stale path, when checked, then TICK007 fires and the fix is `frob ticket reindex`"
bound = false

[[acceptance]]
text = "Given all files at computed paths, when checked, then it does not fire"
bound = false
+++

Implements navigation.md section 2.2.

On the tip of the branch every ticket file is at its computed path; the fix is frob ticket reindex.
