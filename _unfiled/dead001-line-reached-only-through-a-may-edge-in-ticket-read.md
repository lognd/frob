+++
id = "01M62AM9SH454DCNWR0ATTCAPV"
title = "DEAD001 'line' reached only through a May edge in ticket/read.rs"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T22:38:26Z"
updated = "2026-11-16T17:31:23Z"
labels = ["no-story"]
scope = ["crates/frob/src/ticket/read.rs"]

[[acceptance]]
text = "Given crates/frob/src/ticket/read.rs, when frob check runs, then DEAD001 no longer reports EvidenceView::line as reached only through a May edge"
bound = true
+++

found while working ~5E5N62X; pre-existing (blame 2026-10-21), not in that diff
