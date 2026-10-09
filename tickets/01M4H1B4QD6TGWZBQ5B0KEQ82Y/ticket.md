+++
id = "01M4H1B4QD6TGWZBQ5B0KEQ82Y"
title = "Plan IR: P- subject/formula split, unresolved-when conditions and report notes, so the outcome layer can run from a plan alone"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-09T19:13:21Z"
updated = "2026-10-09T20:37:29Z"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/plan/ir.rs", "crates/gob-plan/src/plan/codec.rs", "crates/gob-plan/src/plan/validate.rs", "crates/gob-plan/src/plan/tests/props.rs", "crates/gob-plan/src/plan/mod.rs", "crates/gob-plan/src/plan/tests/mod.rs", "crates/gob-plan/tests/support/mod.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EYANWG9GE031G17RK4A"

[[acceptance]]
text = "Given a P- plan whose find carries a subject filter, when the plan is encoded, decoded and validated, then the validator accepts the split and rejects a report-when in a P- plan"
bound = false

[[acceptance]]
text = "Given a plan with an unresolved-when condition, when encoded and decoded, then the condition and its reason round-trip and the condition is reachable by the validator"
bound = false
+++

found while working ~G17RK4A, needed by ~BP7TEN3. PlanParts.clauses is one flat list, so a P- rule's subject filter (find f: function where f is public) cannot be told from the good-thing formula (spec 7.0.5: F=No fires), and the IR has no unresolved-when condition (spec 7.0.5) or report notes. Add a subjects count (leading clauses that select subjects), an unresolved list of (condition, reason string), and the P- report-when validator rule; bump the codec and proptest generators. Coordinate with ~MXNZT4A, which edits the same files.
