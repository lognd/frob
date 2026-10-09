+++
id = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"
title = "Plan executor outcomes: polarity, unresolved when, one finding per binding, witnesses, budgets"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-09T23:15:28Z"
idempotency_key = "m2-exec-outcome"
labels = ["milestone:2", "area:grl", "creates:crates/gob-plan/tests/exec_outcome.rs"]
scope = ["crates/gob-plan/src/exec/outcome/**", "crates/gob-plan/src/exec/mod.rs", "crates/gob-plan/src/exec/core/mod.rs", "crates/gob-plan/src/exec/core/eval.rs", "crates/gob-plan/src/exec/core/verdict.rs", "crates/gob-plan/src/exec/relations/mod.rs", "crates/gob-plan/tests/exec_outcome.rs", "crates/gob-plan/tests/support/mod.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EYANWG9GE031G17RK4A"

[[acceptance]]
text = "Given a P+ rule whose pattern holds only through May edges, when executed, then the outcome is Unresolved; given a P- rule whose good thing is absent even on May edges it fires, and present on Must facts it is clean"
bound = true

[[acceptance]]
text = "Given two `report ... when` clauses that both hold for one binding, when executed, then exactly one finding is produced from the first in text order, naming the first witness by (path, offset)"
bound = true
+++

Implements grl-spec.md sections 7.1 and 7.2; rules.md section 2.

Polarity decides fire, Unresolved or clean per binding with no author code; NotApplicable is counted once per language and never a finding; parse-error nodes and budget overruns are Unresolved.
