+++
id = "01M4GXG47NK6T1WBBPCMXNZT4A"
title = "Plan IR: count, knob and def-call ops so the executor's count/knobs/defs are reachable from a rule"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-09T18:06:10Z"
updated = "2026-10-09T20:30:42Z"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/plan/ir.rs", "crates/gob-plan/src/plan/codec.rs", "crates/gob-plan/src/plan/validate.rs", "crates/gob-plan/src/plan/tests/props.rs", "crates/gob-plan/src/exec/relations/count.rs", "crates/gob-plan/src/exec/core/eval.rs", "crates/gob-plan/src/exec/core/mod.rs", "crates/gob-plan/src/plan/limits.rs", "crates/gob-plan/src/plan/mod.rs", "crates/gob-plan/src/plan/error.rs", "crates/gob-plan/src/plan/tests/mod.rs", "crates/gob-plan/tests/support/mod.rs", "crates/gob-plan/tests/exec_relations.rs", "crates/gob-plan/src/exec/core/verdict.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EYANWG9GE031G17RK4A"

[[acceptance]]
text = "Given a plan with a count-versus-knob comparison, when encoded, decoded and executed with a [rules] override, then the threshold changes and the codec round-trips"
bound = true

[[acceptance]]
text = "Given a def called twice with the same arguments, when executed, then its body is evaluated once (materialised view) and a recursive or forward def call is refused by the validator"
bound = true
+++

found while working ~G17RK4A. The plan IR (plan/ir.rs, format VERSION 1) has no count, knob or def-call op, so the executor ships Count intervals, Knobs and count() as a Rust API (exec/relations) that no compiled rule can reach yet. Add the ops (a count comparison against an int or a knob with default, a def table and call), bump the codec, extend the validator (GRL009 non-recursion, tree property) and the proptest generators, and evaluate defs as memoised views per grl-spec.md 7.0.2.
