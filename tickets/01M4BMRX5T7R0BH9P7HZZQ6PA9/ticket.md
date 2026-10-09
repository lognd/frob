+++
id = "01M4BMRX5T7R0BH9P7HZZQ6PA9"
title = "ticket doable takes about 23 s on this repository"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-07T16:57:28Z"
updated = "2026-10-09T19:04:31Z"
idempotency_key = "ticket-doable-slow"
labels = ["milestone:2", "area:pm"]
scope = ["crates/frob-ledger/src/**", "crates/frob/src/ticket/**", "crates/frob-lease/src/**"]

[[acceptance]]
text = "Given this repository's ledger, when ticket doable runs, then the done-report names where the time goes (-vv log counts) and the fix removes the per-ticket repeated work, with a test asserting the repeated step runs once"
bound = true
+++

Measured 2026-10-07 by the ~9VT321D implementer: ticket doable takes about 23 s on the primary repo (debug binary). Not investigated; suspected per-ticket lease or events reads, the same N+1 shape as board before ~9VT321D.
