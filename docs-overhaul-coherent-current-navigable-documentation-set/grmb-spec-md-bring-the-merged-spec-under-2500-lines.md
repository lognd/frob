+++
id = "01M69AHEBM4Q457KYJR2TSHHNP"
title = "grmb-spec.md: bring the merged spec under 2500 lines"
type = "docs"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:51:33Z"
updated = "2026-11-01T17:33:50Z"
idempotency_key = "grmb-cycle1-spec-length"
scope = ["docs/design/grmb-spec.md", "docs/design/tickets.md", "docs/design/pm-enforcement.md", "docs/design/code-model.md", "crates/grimble-model/src/refspec.rs", "notes/research/grmb-evidence/cycles.md"]

[[acceptance]]
text = "grmb-spec.md is under 2800 lines with no normative content lost: frob-join sections 17.2-17.6 are in pm-enforcement.md 9, document anchors and runner ids (4.5.1, 4.5.3) in code-model.md 2, and the U encoding and formal relation (old 9-10) in code-model.md 11-12, each replaced by a pointer; the remaining gap to 2500 is tracked in a follow-up ticket"
bound = false
+++

Follow-up of ~MHGA5VN cycle 1 (DOC4): the merge cut 3393 lines to about 2900 but the frob-owned sections live outside the lease of that ticket.
