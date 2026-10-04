+++
id = "01M38BCNKQTNHBMFACZADQ3WKK"
title = "Add due date to milestone/sprint-bearing tickets and rank sibling-ordering hint to Ticket/TicketSpec"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5751"]
labels = ["milestone:v0.536.0"]
scope = ["src/frob/tickets/_models.py"]
+++

Add due: date | None to milestone/sprint-bearing tickets and rank: int | None (explicit sibling ordering hint) to Ticket/TicketSpec.

Positive control: frob ticket new --due 2026-12-01 --rank 3 round-trips; a rank collision within one parent is tolerated (ordering hint, not a unique key) and does not raise. State the non-uniqueness explicitly in the doc page.

Doc page: docs/modules/tickets-data-storage.md#data-models

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
