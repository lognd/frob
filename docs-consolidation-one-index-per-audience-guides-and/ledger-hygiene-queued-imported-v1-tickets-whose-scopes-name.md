+++
id = "01M4H0X0TZN5ZDTBF1GSW12ZDZ"
title = "Ledger hygiene: queued imported v1 tickets whose scopes name v1 doc paths (docs/modules, docs/strata, docs/guide) get a v2 scope or are dropped with a reason"
type = "chore"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:38Z"
updated = "2026-10-10T00:52:27Z"
idempotency_key = "docs-consolidation-2026-10-09-p8"
scope = ["changelog.d/**"]

[[acceptance]]
text = "Given the todo tickets whose scope names a path under docs/modules, docs/strata or docs/guide, when phase 8 is done, then each has a v2 scope or is dropped with a recorded reason, and no todo ticket scope names a docs path absent at HEAD"
bound = true
+++

Phase 8 of notes/review/docs-consolidation-2026-10-09.md (section 2.3, last bullet). Ledger edits only (`frob ticket update`, `frob ticket drop`).
