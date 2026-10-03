+++
id = "01M3ZX7J3BDD63R1SJ1H3KZPCX"
title = "Benchmark B1: plan executor versus handwritten Rust on three std rules"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:34:24Z"
idempotency_key = "m2-bench-b1"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/benches/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F57JCT6CZXY5VS9RHTR"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HW6V59EBYZ2A0HC06TD"

[[acceptance]]
text = "Given TODO001, DOC002 and COV001 as plans and as handwritten Rust on the 100k-line fixture, when the bench runs, then the per-file ratio is reported and the gate fails above 1.3x"
bound = false

[[acceptance]]
text = "Given findings from both forms, when compared, then they are equal"
bound = false
+++

Implements plugins.md section 6.6 (B1).

Criterion bench, scheduled in CI; target within 1.3x per file on three std rules.
