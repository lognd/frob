+++
id = "01M6BYD4FKAV3ZS56KZV62E76Z"
title = "Smoke: fresh repo fails check on PACK005 lock key and PM033"
type = "bug"
category = "todo"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T16:17:12Z"
updated = "2026-11-01T16:17:12Z"
scope = ["crates/gob-packs/src/activation.rs", "crates/frob-pm/src/eval/replenish.rs"]

[[acceptance]]
text = "Given a fresh frob init repo, when frob check --ticket runs, then no PACK005 warning and no PM033 error appear"
bound = false
+++
