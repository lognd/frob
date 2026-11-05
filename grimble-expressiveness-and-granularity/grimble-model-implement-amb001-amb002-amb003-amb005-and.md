+++
id = "01M6P033P70RJ9JZJ5NWV5AWNB"
title = "grimble-model: implement AMB001, AMB002, AMB003, AMB005 and AMB007 rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T13:59:05Z"
updated = "2026-11-05T15:27:43Z"
scope = ["crates/grimble-model/src/rules/**", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/tests/**", "docs/**", "crates/grimble/src/explain_cmd.rs"]

[[acceptance]]
text = "Given the rev 2 rule tables, when this lands, then AMB001, AMB002, AMB003, AMB005 and AMB007 are implemented in crates/grimble-model/src/rules with colocated md and corpus fixtures, and their tests pass"
bound = true
+++
