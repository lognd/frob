+++
id = "01M4Z1MYXBWTWH9F271FEY3NSE"
title = "Land train: union affected-cone check and bound-evidence reuse across a candidate"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:05Z"
updated = "2026-10-15T21:27:17Z"
idempotency_key = "train-cone"
labels = ["area:land", "creates:crates/frob-land/src/train_check.rs"]
scope = ["crates/frob-land/src/train_check.rs", "crates/frob-check/src/diff_base.rs", "crates/frob-land/src/lib.rs", "docs/design/build-test-ci.md", "changelog.d/01M4Z1MYXBWTWH9F271FEY3NSE.changed.md"]

[[links]]
kind = "blocked-by"
target = "01M4Z1MYF3JKB73KCCX5BPJ7WJ"

[[links]]
kind = "blocked-by"
target = "01M4Z1MYPEJ6HDVBJVPDVHR8MA"

[[links]]
kind = "blocked-by"
target = "01M4Z295BVX8CRG8N4F7415NG4"

[[acceptance]]
text = "Given a candidate of N tickets, when checked, then one check runs over the union of cones"
bound = true

[[acceptance]]
text = "Given member evidence still valid for the candidate, then it is reused not re-run"
bound = true

[[acceptance]]
text = "Given a red check, then the failing evidence is returned for the bisection planner"
bound = true

[[acceptance]]
text = "Given a candidate, then per-member cheap ticket rules run per member, one diff_base tool run covers the union, and the ratchet runs once"
bound = true
+++

Run ONE check over the candidate using the union of member cones (docs/design/build-test-ci.md Fast lands, union of cones; Unknown/May edges widen), shared target dir. Bound evidence of members is reused when its inputs are unchanged by the candidate; otherwise re-run once for the union. Expose a CandidateChecker implementing the planner Runner trait with failing evidence attributed per ticket where possible.
