+++
id = "01M5V73ZX5V2VNBKHCQ9YD3YC3"
title = "examples/cells.rs names_callee duplicates grimble-bind"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-26T04:22:24Z"
updated = "2026-10-26T04:22:24Z"
scope = ["crates/grimble-capabilities/examples/**"]

[[acceptance]]
text = "names_callee in examples/cells.rs is replaced by the grimble-bind implementation"
bound = false
+++

Found while working ~FKKYQ41. names_callee in examples/cells.rs duplicates the logic in grimble-bind; extract or reuse it.
