+++
id = "01M3ZXGAWKZPVY6HF9NJ8GAFQV"
title = "frob ticket proposals list and decline, and the pending count in check"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:39:12Z"
updated = "2026-10-03T05:51:56Z"
idempotency_key = "m2-ticket-proposals-verbs"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/ticket/proposals_cmd.rs", "crates/frob-check/src/proposals_summary.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[acceptance]]
text = "Given a pending proposal, when accepted, then the ticket field changes through a recorded event and the proposal is closed"
bound = false

[[acceptance]]
text = "Given pending proposals, when frob check runs, then exit status is unaffected and the summary shows the count"
bound = false
+++

Implements mirror.md section 3.5.

List pending proposals (tracker item id, field, actor id, time, digest, capped escaped excerpt, origin tracker); decline records a reason and appends proposal-declined; frob check shows a summary count (Advisory), never a failure. Text from the tracker carries origin=tracker and is escaped (security.md 2.10). Accept with its guards is a separate ticket (m2-mirror2-accept-guards).
