+++
id = "01M67CF0W52MK6V31FN6DP3TY9"
title = "CAP: MDL008 when provides S is not owned by the declaring node"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T21:46:42Z"
updated = "2026-11-19T16:11:14Z"
labels = ["good-first", "no-story"]
scope = ["crates/grimble-bind/src/caps.rs,crates/grimble-model/src/**,docs/design/grimble-capabilities-v3.md"]

[[acceptance]]
text = "Given a model whose node declares provides C via S where S is not owned by that node, when the model is checked, then MDL008 is raised in a model test"
bound = true
+++

Follow-up from 01M666NX8TN1R3X13Q4S9CTJ1V (provides C via S boundary).

## Start here
Find where the model checks a `provides C via S` boundary in crates/grimble-model (search for MDL008), then add the missing check: S must be a node owned by the declaring node. Add a model test next to the existing MDL008 cases.
no-story: internal engineering task in grimble-model; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
