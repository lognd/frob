+++
id = "01M5C7AA29V08HTNZM0BA2A6ST"
title = "Plan executor is 4.6x-63x slower than handwritten on B1 (target 1.3x)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T08:37:15Z"
updated = "2026-10-20T09:45:21Z"
scope = ["crates/gob-plan/src/**"]
+++

found while working ~H3KZPCX: median per-file ratios TODO001 4.58x, COV001 25.2x, DOC002 63.4x; bench b1_plan_vs_handwritten exits non-zero
