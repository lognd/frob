+++
id = "01M3Z712AFAG3GCEAZ66KPBWD1"
title = "Unresolved gate: fail_on_unresolved knob, required marks, exit 1"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:06:23Z"
idempotency_key = "m2-gate"
labels = ["milestone:2"]
scope = ["crates/gob-diagnostics/**", "crates/frob-check/**", "crates/frob/**", "docs/reference/**", "docs/schemas/**"]

[[acceptance]]
text = "Given a required Unresolved finding and fail_on_unresolved = required, when frob check runs, then exit is 1 and the summary names the required reason"
bound = false

[[acceptance]]
text = "Given a non-required Unresolved finding, when frob check runs with the default knob, then exit is 0 and the finding is counted in the summary"
bound = false
+++

cli.md section 2 (D61): Unresolved is orthogonal to the threshold; add [check] fail_on_unresolved = required|never|all (default required) as a materialized knob; mark required Unresolved findings (configured sibling absent or incompatible, annotation-required opaques on the public surface under [compute], must_measure rules with zero subjects) on FindingRecord; gob-diagnostics fail_on no longer skips Unresolved: required ones fail with exit 1; frob-check wires the knob; docs regenerated.
