+++
id = "01M6ABTQZE6E047SKG212CQ663"
title = "relation.rs Term::units quadratic callers (~7s)"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T01:33:21Z"
updated = "2026-11-01T01:33:21Z"
idempotency_key = "perf-relation-units"
scope = ["crates/grimble-bind/src/relation.rs,crates/gob-ir/**"]

[[acceptance]]
text = "Term::units callers are linear in term size, with a count-based regression test"
bound = false
+++

Follow-up of YNRQJ09: relation.rs costs about 7s cold from quadratic Term::units callers.
