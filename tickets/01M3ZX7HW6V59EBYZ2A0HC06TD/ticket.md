+++
id = "01M3ZX7HW6V59EBYZ2A0HC06TD"
title = "Acceptance corpus A: TODO001, DOC002, COV001, INV002, SCOPE001, NEAT013 written in GRL"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:35:00Z"
idempotency_key = "m2-grl-ten-a"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/tests/ten_rules/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7F8WQQ8JKW7GVVB2EYG6"

[[links]]
kind = "relates"
target = "01M3ZVQAA1DNM1BJ5TZG5B3CFR"

[[acceptance]]
text = "Given the six .grl files, when `rule test` runs, then every example passes"
bound = false

[[acceptance]]
text = "Given the same six rules and the hand-written Rust versions on this repository, when both run, then findings agree or each difference is recorded in the ticket"
bound = false
+++

Implements grl-spec.md sections 12 and 13.3; plugins.md section 11 (frob families stay tier 0).

The first six section 12 rules as .grl files with their fire and clean examples, kept as acceptance fixtures, NOT registered in the std pack (the hand-written tier-0 rules keep their ids).
