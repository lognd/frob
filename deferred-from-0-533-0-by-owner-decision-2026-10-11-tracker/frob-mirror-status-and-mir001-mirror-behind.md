+++
id = "01M3ZX84DHC5PSS7H0Z1NMMJMQ"
title = "frob mirror status and MIR001 mirror-behind"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T05:51:57Z"
idempotency_key = "m2-mirror-status"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/status.rs", "crates/frob-obligations/src/mir.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX841SP0ZXM4CT18A4B8CV"

[[acceptance]]
text = "Given three unpublished events, when `frob check` runs, then MIR001 reports behind by 3 events since the last publish time"
bound = false

[[acceptance]]
text = "Given a fully published mirror, when check runs, then no MIR001 is emitted"
bound = false
+++

Implements mirror.md section 3 (tracker or network down).

MIR001 is Unresolved, not required by default: the mirror is behind by N events since a time. Never silent.
