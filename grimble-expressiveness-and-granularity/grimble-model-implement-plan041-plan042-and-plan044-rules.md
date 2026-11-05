+++
id = "01M6P033S4VV7JST84C3Q0TF80"
title = "grimble-model: implement PLAN041, PLAN042 and PLAN044 rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T13:59:05Z"
updated = "2026-11-05T15:46:23Z"
scope = ["crates/grimble-model/src/rules/**", "crates/grimble/src/explain_cmd.rs", "docs/reference/rules/**", "docs/README.md"]

[[acceptance]]
text = "Given the rev 2 rule tables, when this lands, then PLAN041, PLAN042 and PLAN044 are implemented in crates/grimble-model/src/rules with colocated md and corpus fixtures, and their tests pass"
bound = false
+++
