+++
id = "01M67CF0W52MK6V31FN6DP3TY9"
title = "CAP: MDL008 when provides S is not owned by the declaring node"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T21:46:42Z"
updated = "2026-10-30T21:46:42Z"
scope = ["crates/grimble-bind/src/caps.rs,crates/grimble-model/src/**,docs/design/grimble-capabilities-v3.md"]

[[acceptance]]
text = "provides with unowned or foreign-owned S raises MDL008 in a model test"
bound = false
+++

Follow-up from 01M666NX8TN1R3X13Q4S9CTJ1V (provides C via S boundary).
