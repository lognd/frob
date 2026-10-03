+++
id = "01M4069RPPQE1ES1914K6V6Y0D"
title = "frob cycle new and close (carry-over events, retro note, commitment ratio)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:54Z"
updated = "2026-10-03T11:08:40Z"
idempotency_key = "m2-rel-cycle-new-close"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/cycle/lifecycle.rs", "crates/frob/src/cycle_cmd.rs", "crates/frob-pm/src/event.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069QWSJEH5KW8K0YR8CA0D"

[[links]]
kind = "blocked-by"
target = "01M4069R19D2KZENDGEH83JZSW"

[[acceptance]]
text = "Given a cycle with an unfinished ticket, when frob cycle close runs, then the ticket carries to the next cycle and the ratio is recorded"
bound = false

[[acceptance]]
text = "Given a member in-progress with a live lease, when close runs, then it exits 3 naming the ticket"
bound = false
+++

`cycle new --start --end --goal [--capacity-points]` (end defaults from [pm] cycle_days) and `cycle close` per pm-enforcement.md 4: incomplete members carry to the next cycle with a cycle event (op carried), the commitment-versus-done ratio is recorded, close refuses while a member is in-progress with a live lease (E-CYCLE-LEASE).
