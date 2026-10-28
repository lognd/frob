+++
id = "01M55NRV7E8Q4C5Q21QWKS14DV"
title = "crunk-rules: decide ORG001/ORG002/ORG004 honoring [org].ignore and tokens sheet"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-17T19:35:10Z"
updated = "2026-10-28T12:56:04Z"
idempotency_key = "crunk-cmp-orgignore"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given the decision, when documented and tested, then Rust and docs agree"
bound = false
+++

Rust ORG001 filters by [org].ignore and ORG004 gates on tokens_only_custom_props; Python does neither. Decide: match Python or document the extension in docs/crunk.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
