+++
id = "01M3ZX7WVFZCG88424XW0FP3WH"
title = "Resource caps for plans and findings: budget Unresolved on breach"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-03T03:34:35Z"
idempotency_key = "m2-sec-plan-caps"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-plan/src/limits.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[acceptance]]
text = "Given a plan exceeding its step counter, when executed, then the rule is Unresolved budget for that file and other rules still run"
bound = false

[[acceptance]]
text = "Given a regex over the size limit, when a pack is loaded, then it is rejected at load with a located error"
bound = false
+++

Implements security.md section 2.5 (resource caps).

Findings per file, bytes per message, total output bytes, a step counter for tier-2 plans, regex size and nesting limits at load; any breach is Unresolved budget.
