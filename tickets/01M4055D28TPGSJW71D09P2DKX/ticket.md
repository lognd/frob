+++
id = "01M4055D28TPGSJW71D09P2DKX"
title = "ticket update: add, replace and remove acceptance criteria (repeatable flags, no comma splitting)"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:53:02Z"
updated = "2026-10-03T06:06:29Z"
idempotency_key = "m2-ticket-update-acceptance"
labels = ["milestone:2"]
scope = ["crates/frob-ledger/**", "crates/frob/**", "docs/design/tickets.md", "docs/design/cli.md", "docs/reference/cli/frob.md"]

[[acceptance]]
text = "Given a ticket with two criteria, when ticket update --add-acceptance with a comma in its text runs, then the ticket has three criteria and the third holds the full text"
bound = false

[[acceptance]]
text = "Given a criterion with bound evidence, when it is removed, then the command reports the evidence that loses its criterion"
bound = false
+++

Found by the mirror re-cut: ticket update cannot change acceptance, because --set splits list values on commas and acceptance text contains commas, so planners record changed acceptance in decision comments instead of the bound list. Add --add-acceptance TEXT (repeatable), --remove-acceptance INDEX (repeatable, 1-based as shown by show), and --clear-acceptance; each change is a field event with the old and new list; bound evidence on a removed criterion is reported, not silently dropped. Same pattern as --add-scope and --remove-scope (~V5F85PC).
