+++
id = "01M3ZX7JHQQ3BVZWFMPAW40T13"
title = "Benchmark B2: compiled-in GRL rule versus the same rule as a cached disk plan"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-20T10:00:19Z"
idempotency_key = "m2-bench-b2"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/benches/**", "crates/gob-plan/Cargo.toml", "Cargo.lock", "docs/design/build-test-ci.md", "crates/gob-packs/Cargo.toml", "crates/gob-packs/benches/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7HN0YF3SYGVJRT5H07H5"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HW6V59EBYZ2A0HC06TD"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JE252WBVE5DKMJK3JME"

[[acceptance]]
text = "Given one rule compiled in and as a disk-loaded cached plan, when the bench runs, then the ratio is reported and the gate fails above 1.3x"
bound = true

[[acceptance]]
text = "Given the two runs, when their JSON is compared, then it is identical"
bound = true
+++

Implements plugins.md section 6.6 (B2).

Target: disk plan within 1.3x of compiled-in after the plan cache is warm, findings identical.
