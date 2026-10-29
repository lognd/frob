+++
id = "01M63B7F02SKSJCQG7TMXQ4HW5"
title = "Wire rule nature attribute, envelope fields and agent detection"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-29T08:08:08Z"
updated = "2026-10-29T08:08:08Z"
idempotency_key = "followup-291TPEB-nature-wiring"
scope = ["crates/gob-macros/**", "crates/gob-rules/**", "crates/gob-cli/**"]

[[acceptance]]
text = "#[rule(nature = heuristic)] flows to RuleDef and the output envelope (nature, waivable_by)"
bound = false

[[acceptance]]
text = "Agent vs human audience is detected by the CLI and selects HeuristicNote::message"
bound = false
+++

Follow-up from ~291TPEB: gob-rules::nature exists but is not wired. no-story: internal engineering task.
