+++
id = "01M55NRTXCM47FXCQ6SK0ZA3XB"
title = "crunk-rules: ORG002 BEM split and per-segment checks (match Python)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-10-27T02:58:20Z"
idempotency_key = "crunk-cmp-org002"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given .card__title--active, when ORG002 runs, then it is clean"
bound = false
+++

Rust ORG002 requires a lowercase first char with no BEM split (org/mod.rs). Python splits on __ and -- and checks each segment, so .card__title--active is clean. See comparison with lognd/crunk.
