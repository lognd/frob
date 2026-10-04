+++
id = "01M30M6G28XT6EAT5WJCEQTSNN"
title = "T-5105 blocked_by references T-draft-a693d397 which does not exist in the ledger"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5192"]
scope = ["tickets/T-5105/ticket.md"]
+++

found while land-prep dispatch on worktree t-draft-af37d815: T-5105's blocked_by lists T-draft-a693d397, which has no ticket.md anywhere under tickets/ or tickets/archive/ (never created or promoted) -- start refuses with BlockerOpen and cannot be cleared without either creating that ticket or removing the dangling blocker

## Drop reason
- 2026-09-22: T-5105's dangling blocker was cleared on dev and T-5105 landed
