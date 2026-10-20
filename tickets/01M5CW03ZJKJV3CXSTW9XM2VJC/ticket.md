+++
id = "01M5CW03ZJKJV3CXSTW9XM2VJC"
title = "Fix tickets.md section 2b drift"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 1
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T14:51:37Z"
idempotency_key = "dt-DT03"
scope = ["docs/design/tickets.md"]

[[acceptance]]
text = "docs/design/tickets.md section 2b no longer cites a [land] push key and describes the doctor accurately (no unpushed-commit listing); each claim is checked against crates/frob-land/src/base_ci.rs (LandConfig) and crates/frob-ledger/src/doctor.rs"
bound = false
+++

No [land] push key exists; correct the doctor unpushed-commit claim. See docs/design/distributed-tickets.md.
