+++
id = "01M3ZX7E2DPA2CXBAQ8ZKM5W7Y"
title = "GRL structural checks: GRL009, GRL010, GRL011, GRL012, GRL014"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-08T14:01:42Z"
idempotency_key = "m2-grl-check-structure"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/check/structure.rs", "crates/gob-plan/src/check/mod.rs", "crates/gob-plan/src/check/render.rs", "crates/gob-plan/tests/**", "crates/gob-plan/Cargo.toml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"

[[acceptance]]
text = "Given a def that calls itself, a closure without `within`, an explain without `## Remedy` and a rule using `diff.changed` without `needs diff`, when compiled, then GRL009, GRL010, GRL012 and GRL014 are emitted with their goldens"
bound = true

[[acceptance]]
text = "Given a rule without a clean example, when compiled, then GRL011 is emitted with a scaffold of the missing example"
bound = true
+++

Implements grl-spec.md sections 7.4, 9 and 10.

Boundedness and completeness checks: def recursion and forward reference, closure without within, missing fire or clean example (plus the universal third example), explain without Remedy, side relation used without needs.
