+++
id = "01M6FQG1166C9AAC33P0F026VB"
title = "PM010 honors recorded over-commit events"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-03T03:33:25Z"
updated = "2026-11-03T04:04:09Z"
idempotency_key = "pm010-overcommit"
scope = ["crates/frob-pm/src/legacy/cycle_plan.rs", "docs/design/frob/pm-and-releases.md", "docs/reference/rules/PM010.md"]

[[acceptance]]
text = "A commitment at or below a recorded over-commit is not flagged by PM010"
bound = false
+++

PM010 documented --over-commit --reason as its remedy but ignored the recorded event, so CI failed with 410 > 355.
