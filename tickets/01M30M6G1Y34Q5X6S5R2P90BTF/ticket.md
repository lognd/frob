+++
id = "01M30M6G1Y34Q5X6S5R2P90BTF"
title = "DOC011: docs/design/ticket-strata-shared-graph-inventory.md cites three draft ids (T-draft-5d5c1eb2, e7434c27, 452acd80) that were never filed"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:00Z"
aliases = ["T-5182"]
labels = ["milestone:0.534.0", "v1-cluster:B3d"]
scope = ["docs/design/ticket-strata-shared-graph-inventory.md"]
+++

MEASURED 2026-09-21 05:05 after T-3032 landed: DOC011 x3 at lines 38, 46 and 60 -- the inventory's follow-up column names T-draft-5d5c1eb2, T-draft-e7434c27 and T-draft-452acd80 as filed follow-ups, but no ticket with those ids exists on dev (not in tickets/ nor the archive) and the t-3032 worktree never held ticket dirs for them. Either file the three follow-ups (cycle refusal on blocked_by/parent mutation is one of them) and rewrite the citations to the real ids, or reword the rows to 'not yet filed'. Verify: DOC011 on this file 3 -> 0. Related pre-existing DOC011 draft citations: docs/design/registry/{system-design,supply-chain,secrets}.yaml, docs/modules/tickets.md, docs/modules/tickets-lifecycle.md.
