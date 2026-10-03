+++
id = "01M4052TVNPHH7H9Z2M4A453RQ"
title = "Render limits and per-ticket isolation"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-render-limits"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/limits.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83T22GTC94BW4PM742G1"

[[acceptance]]
text = "Given a projection whose body is 65537 characters, when planned, then MIR001 is reported for that ticket and no write is made for it"
bound = false

[[acceptance]]
text = "Given one over-limit ticket among ten, when a run executes, then the other nine are published"
bound = false

[[acceptance]]
text = "Given a label over its length limit, when planned, then the ticket is isolated with a reason"
bound = false
+++

Implements mirror.md section 3.6 (Publishing safely; MIR-AUD-18, 19).

Body size (65536 characters), label count and length and sub-issue limits are checked before any write. A ticket that cannot be published is isolated: MIR001 for that ticket only, and the run continues.
