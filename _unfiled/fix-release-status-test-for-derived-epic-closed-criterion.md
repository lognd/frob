+++
id = "01M7C0NP7PDEG4TAERS90D3M8V"
title = "Fix release_status test for derived epic-closed criterion"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-11-14T03:12:31Z"
updated = "2026-11-14T03:27:37Z"
scope = ["crates/frob/tests/it/release_status.rs"]

[[acceptance]]
text = "Given a member epic left open, when release status runs, then the derived epic-closed criterion is listed as unbound-criterion before the open-ticket blocker"
bound = true
+++
