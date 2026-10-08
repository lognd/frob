+++
id = "01M4CTE4TWJP2W6EV2PZN62TQN"
title = "crunk applies exceptions (crunk-check/src/product.rs 78) and gob-check owns binding (audit M4)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:42Z"
updated = "2026-10-08T03:55:42Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given a crunk finding covered by a frob:waive exception, when crunk check runs, then it is reported as excepted, not open"
bound = false
+++

notes/review/audit-2026-10-07.md M4.
