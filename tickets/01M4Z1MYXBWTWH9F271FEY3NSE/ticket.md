+++
id = "01M4Z1MYXBWTWH9F271FEY3NSE"
title = "Land train: union affected-cone check and bound-evidence reuse across a candidate"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:05Z"
updated = "2026-10-15T05:48:37Z"
idempotency_key = "train-cone"
labels = ["area:land", "creates:crates/frob-land/src/train_check.rs"]
scope = ["crates/frob-check/**", "crates/frob-land/src/train_check.rs"]

[[links]]
kind = "blocked-by"
target = "01M4Z1MYF3JKB73KCCX5BPJ7WJ"

[[acceptance]]
text = "Given a candidate of N tickets, when checked, then one check runs over the union of cones"
bound = false

[[acceptance]]
text = "Given member evidence still valid for the candidate, then it is reused not re-run"
bound = false

[[acceptance]]
text = "Given a red check, then the failing evidence is returned for the bisection planner"
bound = false
+++

Run ONE check over the candidate using the union of member cones (docs/design/build-test-ci.md Fast lands, union of cones; Unknown/May edges widen), shared target dir. Bound evidence of members is reused when its inputs are unchanged by the candidate; otherwise re-run once for the union. Expose a CandidateChecker implementing the planner Runner trait with failing evidence attributed per ticket where possible.
