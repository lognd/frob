+++
id = "01M3ZXGAWKZPVY6HF9NJ8GAFQV"
title = "frob ticket proposals list|accept|decline and the pending count in check"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:39:12Z"
updated = "2026-10-03T03:39:12Z"
idempotency_key = "m2-ticket-proposals-verbs"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-ledger/**", "crates/frob/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZXGAS3HJR9NYAMKWYGETZK"

[[acceptance]]
text = "Given a pending proposal, when accepted, then the ticket field changes through a recorded event and the proposal is closed"
bound = false

[[acceptance]]
text = "Given pending proposals, when frob check runs, then exit status is unaffected and the summary shows the count"
bound = false
+++

mirror.md 3.1. list pending proposals; accept applies the change through the normal ticket verbs as an event authored by the accepter citing the tracker user, then the next mirror run re-publishes; decline records a reason. frob check shows a summary count (Advisory), never a failure. Text from the tracker carries origin=tracker and is escaped (security.md 2.10).
