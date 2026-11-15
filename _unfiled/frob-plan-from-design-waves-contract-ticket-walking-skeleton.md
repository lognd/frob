+++
id = "01M7EXXPTMRWQFK5SJ48GVH66V"
title = "frob plan --from-design --waves: contract ticket, walking skeleton, ordered waves (G19,G20)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:22:12Z"
updated = "2026-11-15T06:22:12Z"
labels = ["no-story"]

[[acceptance]]
text = "plan emits a contract ticket before skeleton and waves"
bound = false

[[acceptance]]
text = "Waves have disjoint owns"
bound = false

[[acceptance]]
text = "Order follows sorry count"
bound = false
+++

Research: ~/projects/frob-research-lifecycle.md rec 5. Contract ticket first, then grimble skeleton, then waves with disjoint node owns ordered by sorry/unknown count. Split follow-up: grimble status --hill.
