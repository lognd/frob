+++
id = "01M5CW03RV49WAJZQ1B76X0RQ0"
title = "Land pushes after the ledger step"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T14:49:53Z"
idempotency_key = "dt-DT01"

[[acceptance]]
text = "Trunk land --push pushes after the ledger step so origin has the land and close commits; orphan mode pushes the ledger branch after the base"
bound = true
+++

Trunk: one push carries code and close. Orphan: push base, then frob-tickets; keep the ticket branch until both succeed. Design sec 3.4. See docs/design/distributed-tickets.md.
