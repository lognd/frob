+++
id = "01M69AHEBM4Q457KYJR2TSHHNP"
title = "grmb-spec.md: bring the merged spec under 2500 lines"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:51:33Z"
updated = "2026-10-31T15:51:33Z"
idempotency_key = "grmb-cycle1-spec-length"
scope = ["docs/design/grmb-spec.md", "docs/design/tickets.md", "docs/design/pm-enforcement.md", "docs/design/code-model.md"]

[[acceptance]]
text = "grmb-spec.md is under 2500 lines with no normative content lost: the frob-join sections (17.2-17.6) move to tickets.md or pm-enforcement.md and the document-anchor and runner-id rules (4.5.1, 4.5.3) move to code-model.md, each replaced by a one-line pointer"
bound = false
+++

Follow-up of ~MHGA5VN cycle 1 (DOC4): the merge cut 3393 lines to about 2900 but the frob-owned sections live outside the lease of that ticket.
