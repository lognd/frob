+++
id = "01M4052VTX4T6W688PQXVTQV56"
title = "MIR001 mirror-behind is time-based, with per-scope reasons"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-03T05:51:39Z"
idempotency_key = "m2-mirror2-mir001"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-obligations/src/mir.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[acceptance]]
text = "Given a last successful run older than N hours, when `frob check` runs, then MIR001 reports the age and no check fails"
bound = false

[[acceptance]]
text = "Given a run that stopped rate-limited, when `frob check` runs, then MIR001 reports rate-limited with the next window"
bound = false

[[acceptance]]
text = "Given a successful run within N hours, when check runs, then no MIR001 is emitted"
bound = false
+++

Implements mirror.md section 3.1 (time-based MIR001) and 3.2 (reasons).

MIR001 reports no successful run for N hours (scheduled runs are delayed, dropped and disabled after inactivity) plus per-scope reasons: rate-limited, budget-too-small, token-blind, marker-key-unknown, a per-ticket render limit or write-not-sticking. It never fails a check or a land.
