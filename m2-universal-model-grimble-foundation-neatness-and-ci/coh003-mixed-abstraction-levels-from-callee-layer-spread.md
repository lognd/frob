+++
id = "01M4CXSSGYVE2QQ7ACW7T5Y51S"
title = "COH003 mixed abstraction levels from callee layer spread"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:29Z"
updated = "2026-10-08T04:54:29Z"
scope = ["changelog.d/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given a unit calling a domain function and raw string slicing beyond max_level_spread, when COH003 runs, then it fires naming both callees and their layers"
bound = false
+++

docs/design/cohesion.md 1; layer from the grimble model or module depth.
