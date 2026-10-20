+++
id = "01M4052V3C65G7JS98ATDGNRJB"
title = "Classify transfer, conversion to a discussion, lock and pin: report, never act"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-classify"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/classify.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052QSA5YKG6MY52BCW6PWV"

[[acceptance]]
text = "Given a transferred issue, when classified, then it is reported and no write is made"
bound = false

[[acceptance]]
text = "Given a locked or pinned issue, when reconciled, then the state is reported and no unlock or unpin is attempted"
bound = false
+++

Implements mirror.md section 3.6 (last bullet).

A transferred issue, one converted to a discussion, and a locked or pinned issue are classified and reported in mirror status, never acted on blindly.
