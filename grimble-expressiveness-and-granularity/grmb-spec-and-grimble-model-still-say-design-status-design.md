+++
id = "01M69VCRMFFJ74SAFPCB9MYY2B"
title = "grmb-spec and grimble-model still say design_status/design_status_hi"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T20:46:05Z"
updated = "2026-10-31T20:55:03Z"
idempotency_key = "design-status-names"
scope = ["docs/design/grmb-spec.md", "docs/design/grimble-model.md"]

[[acceptance]]
text = "grmb-spec.md (PM038, PM047) and grimble-model.md use the shipped names status/status_hi/verified, not design_status/design_status_hi/covered"
bound = false
+++

Found by Q1GEE3D: the shipped export emits status/status_hi/verified (crates/gob-check/src/sibling_doc.rs). grmb-spec.md ~line 2738 and grimble-model.md still use the old names. decisions/ and notes/ are historical; leave them.
