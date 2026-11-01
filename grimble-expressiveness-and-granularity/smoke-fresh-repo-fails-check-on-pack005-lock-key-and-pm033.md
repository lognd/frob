+++
id = "01M6BYD4FKAV3ZS56KZV62E76Z"
title = "Smoke: fresh repo fails check on PACK005 lock key and PM033"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T16:17:12Z"
updated = "2026-11-01T16:49:17Z"
scope = ["crates/gob-packs/src/activation.rs", "crates/frob-pm/src/eval/replenish.rs", "frob.toml", "crates/frob-pm/tests/mdtest/pm033.md", "crates/frob-pm/src/rules/pm033.md"]

[[acceptance]]
text = "Given a fresh frob init repo, when frob check --ticket runs, then no PACK005 warning and no PM033 error appear"
bound = true
+++
