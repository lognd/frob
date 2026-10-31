+++
id = "01M69AHE4GQSD071WYYQ1GEE3D"
title = "rules.md and sibling contract: follow grmb cycle 1 (rule ranges, PLAN041-044, design_status keys)"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:51:33Z"
updated = "2026-10-31T20:27:57Z"
idempotency_key = "grmb-cycle1-rules-sibling"
scope = ["docs/design/rules.md", "docs/design/sibling-contract.md", "docs/schemas/sibling.json"]

[[acceptance]]
text = "rules.md names MDL001-MDL034, the PLAN family incl. PLAN041-PLAN044 and PLAN050-PLAN059, AMB001-AMB009 with grmb-spec.md 16 as the one table home, and states that ERR001-ERR003 are grimble-lints only"
bound = false

[[acceptance]]
text = "sibling-contract.md and sibling.json carry the planning keys design_status, design_status_hi and rollup {declared, bound, covered}"
bound = false
+++

Follow-up of ~MHGA5VN cycle 1: these two files were leased by ERF5VCQ, so the grmb side was renumbered and the shared docs were left for this ticket.
