+++
id = "01M5EFE40AAFRZZEH02757EG2T"
title = "Real --text view for doctor"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:37:37Z"
updated = "2026-10-21T07:30:04Z"
scope = ["crates/frob/src/text_view.rs", "crates/frob/src/doctor.rs"]

[[acceptance]]
text = "frob doctor --text prints aligned sections (toolchain, git, cache, config, ledger, driver, siblings, gc, leases, lands, languages) instead of the generic key dump"
bound = true
+++

Split from ~5JDQ45M: the remaining everyday verbs still fall back to the generic key dump under --text. Reuse crates/frob/src/text_view.rs table helper.
