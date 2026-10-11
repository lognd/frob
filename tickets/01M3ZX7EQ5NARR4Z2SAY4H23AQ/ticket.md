+++
id = "01M3ZX7EQ5NARR4Z2SAY4H23AQ"
title = "Plan cost class and node-kind prefilter computation"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-11T17:16:25Z"
idempotency_key = "m2-plan-cost"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/plan/cost.rs", "crates/gob-plan/src/lower/prefilter.rs", "crates/gob-plan/src/lower/emit.rs", "crates/gob-plan/src/lower/mod.rs", "crates/gob-plan/src/plan/mod.rs", "crates/gob-plan/src/plan/tests/mod.rs", "crates/gob-plan/tests/lower.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[acceptance]]
text = "Given a plan using `reaches ... within 6`, when costed, then the class reads closure depth 6"
bound = true

[[acceptance]]
text = "Given a rule over comment and directive kinds, when lowered, then the prefilter lists exactly those kinds"
bound = true
+++

Implements grl-spec.md section 7.4; plugins.md section 6.2.

Each plan states its cost class (per file, per repository, closure depth N) and the node kinds a file must contain for the rule to run.
