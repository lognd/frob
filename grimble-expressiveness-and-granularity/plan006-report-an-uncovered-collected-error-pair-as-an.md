+++
id = "01M69T6Q3J2RVWGTT4PM7YR6SS"
title = "PLAN006: report an uncovered collected error pair as an obligation (spec 13.2)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T20:25:19Z"
updated = "2026-10-31T22:05:02Z"
idempotency_key = "plan006-obligation"
scope = ["crates/grimble-model/**", "crates/grimble-bind/**", "crates/grimble/src/explain_cmd.rs", "crates/grimble/tests/graph.rs", "docs/design/rules.md", "docs/design/sibling-contract.md", "docs/reference/**"]

[[acceptance]]
text = "PLAN006 fires for a collected (step, variant) pair that is neither handled nor in fails_with, per grmb-spec 13.2, with a test and rules.md entry"
bound = false
+++

Follow-up of DJEDY70, which exposed plan.error_set/plan.collected but left the PLAN006 obligation itself unimplemented. Sequence after WR05MGF/A1A7YMH (same crates).
