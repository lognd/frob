+++
id = "01M6P033KB0H2X52QC73P40F6M"
title = "grimble-model: implement MDL032, MDL033 and MDL034 rules"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T13:59:05Z"
updated = "2026-11-05T14:59:40Z"
scope = ["crates/grimble-model/src/rules/**", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/tests/**", "docs/reference/rules/**", "docs/README.md"]

[[acceptance]]
text = "Given the rev 2 rule tables, when this lands, then MDL032, MDL033 and MDL034 are implemented in crates/grimble-model/src/rules with a colocated md and corpus fixtures, and their tests pass"
bound = true
+++
