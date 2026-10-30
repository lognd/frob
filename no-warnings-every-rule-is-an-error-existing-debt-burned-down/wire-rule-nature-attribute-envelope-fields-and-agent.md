+++
id = "01M63B7F02SKSJCQG7TMXQ4HW5"
title = "Wire rule nature attribute, envelope fields and agent detection"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-29T08:08:08Z"
updated = "2026-10-30T14:16:50Z"
idempotency_key = "followup-291TPEB-nature-wiring"
scope = ["crates/gob-macros/**", "crates/gob-rules/**", "crates/gob-cli/**", "crates/gob-diagnostics/**", "docs/design/rules.md", "docs/reference/rules/**"]

[[acceptance]]
text = "#[rule(nature = heuristic)] flows to RuleDef and the output envelope (nature, waivable_by)"
bound = true

[[acceptance]]
text = "Agent vs human audience is detected by the CLI and selects HeuristicNote::message"
bound = true
+++

Follow-up from ~291TPEB: gob-rules::nature exists but is not wired. no-story: internal engineering task.
