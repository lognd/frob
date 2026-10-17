+++
id = "01M55NRV7E8Q4C5Q21QWKS14DV"
title = "crunk-rules: decide ORG001/ORG002/ORG004 honoring [org].ignore and tokens sheet"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-10-17T19:35:10Z"
idempotency_key = "crunk-cmp-orgignore"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given the decision, when documented and tested, then Rust and docs agree"
bound = false
+++

Rust ORG001 filters by [org].ignore and ORG004 gates on tokens_only_custom_props; Python does neither. Decide: match Python or document the extension in docs/crunk.
