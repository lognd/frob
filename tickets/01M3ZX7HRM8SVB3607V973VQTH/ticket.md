+++
id = "01M3ZX7HRM8SVB3607V973VQTH"
title = "Conformance test: compiled-in std rules equal their plans byte for byte"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:34:24Z"
idempotency_key = "m2-conformance"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/tests/conformance/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F8WQQ8JKW7GVVB2EYG6"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HN0YF3SYGVJRT5H07H5"

[[acceptance]]
text = "Given every std GRL rule, when run both ways on the std corpus and each rule's examples, then the JSON outputs are byte-identical"
bound = false

[[acceptance]]
text = "Given a deliberately divergent generated rule, when the test runs, then it fails naming the rule and the first differing finding"
bound = false
+++

Implements plugins.md section 6.1 (semantics row); security.md section 2.8.

Every std GRL rule runs compiled-in and as a plan on the std corpus and its embedded examples; JSON must be byte-identical; also on an adversarial corpus with randomized paths.
