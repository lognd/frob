+++
id = "01M3ZX7H8FPEAY1X1WVW1PNXXN"
title = "rule why: per-clause trace for one location"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:23Z"
updated = "2026-10-03T03:34:23Z"
idempotency_key = "m2-grl-why"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/why/**", "crates/gob-plan/src/verbs/why.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FCFBJSWMTZGCQMW7215"

[[acceptance]]
text = "Given NOPE001 with `where not d inside test` and a dbg! inside a test, when `rule why NOPE001 src/lexer.rs:17` runs, then it prints the candidate count and `failed: ... is inside test` for that clause"
bound = false

[[acceptance]]
text = "Given a P- rule, when why runs, then the output says which clauses used May edges because of the polarity, and a test shows why and check agree on every location of a corpus"
bound = false
+++

Implements grl-spec.md sections 2 (step 5), 7.2 and 11.

Same engine as check: print candidates per clause, the first failing clause, the edges and polarity used.
