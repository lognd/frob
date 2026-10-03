+++
id = "01M3ZX7EKNE5Q0NB0DKCH77AZX"
title = "Lower a checked rule to a plan with a clause-ordering planner"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-03T03:34:21Z"
idempotency_key = "m2-grl-lower"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/lower/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E2DPA2CXBAQ8ZKM5W7Y"

[[links]]
kind = "blocked-by"
target = "01M3ZX7EG6S2V48F43HP1GM2NQ"

[[acceptance]]
text = "Given the section 12 rules that need no snippets, when lowered, then a plan results for each"
bound = false

[[acceptance]]
text = "Given the same clauses written in two different orders, when lowered, then the plans are byte-identical"
bound = false
+++

Implements grl-spec.md sections 7.1 and 7.4.

Clause order in the source does not matter; the planner orders the work so every plan terminates in polynomial time.
