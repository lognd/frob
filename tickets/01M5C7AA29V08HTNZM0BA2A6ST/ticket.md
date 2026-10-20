+++
id = "01M5C7AA29V08HTNZM0BA2A6ST"
title = "Plan executor is 4.6x-63x slower than handwritten on B1 (target 1.3x)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T08:37:15Z"
updated = "2026-10-20T10:27:52Z"
scope = ["crates/gob-plan/src/**", "crates/gob-plan/tests/exec_relations.rs"]

[[acceptance]]
text = "Reachability through the cached closure keeps may-edge and frontier verdicts"
bound = true

[[acceptance]]
text = "The Fx-hashed map used by executor caches round-trips keys"
bound = true

[[acceptance]]
text = "Executor core results are unchanged by the domain, operand and index caches"
bound = true
+++

found while working ~H3KZPCX: median per-file ratios TODO001 4.58x, COV001 25.2x, DOC002 63.4x; bench b1_plan_vs_handwritten exits non-zero
