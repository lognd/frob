+++
id = "01M3ZX7HGX4HXKW1X8VKHW9BKW"
title = "GRL to Rust codegen against the executor operator library"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:34:24Z"
idempotency_key = "m2-codegen-core"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/codegen/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[acceptance]]
text = "Given a lowered std rule, when generated twice, then the Rust output is byte-identical and compiles with unsafe_code forbidden"
bound = false

[[acceptance]]
text = "Given a generated rule and its plan on the same fixture, when both run, then findings are equal"
bound = false
+++

Implements plugins.md section 6.1; grl-spec.md decision D80.

Std rules are compiled ahead of time into Rust calling the same operator library the plan executor uses, so the hot path has no plan interpretation.
