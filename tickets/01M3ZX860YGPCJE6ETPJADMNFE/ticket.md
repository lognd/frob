+++
id = "01M3ZX860YGPCJE6ETPJADMNFE"
title = "Generated front door: ticket-branch README and epic pages"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-gen-front-door"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/readme.rs", "crates/frob-ledger/src/gen/epic.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a ledger with one epic, one sub-epic and an unfiled ticket, when generated, then the README lists _unfiled first and the epic page groups the sub-epic's tickets"
bound = false

[[acceptance]]
text = "Given a ticket missing from every epic page, when the cross-check runs, then GEN001 reports it"
bound = false
+++

Implements navigation.md sections 3.1 and 3.3.

README.md lists _unfiled first, then epics; each epic page groups tickets by sub-epic and status; every ticket is in exactly one epic page and one status section.
