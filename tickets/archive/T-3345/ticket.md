---
id: T-3345
title: 'COV001: strata-core graph/model.rs+query.rs (33) have zero frob:doc coverage'
state: dropped
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/model.rs
- strata-core/src/graph/query.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob check on main (SHA be9e767) shows 33 unwaived COV001 errors, all in strata-core/src/graph/model.rs (27) and query.rs (6) -- new Rust module shipped with no frob:doc anchors. Single root cause, likely one doc pass or file-level waive with follow-up closes it. Filed from Series ED CI-gate baseline sweep.

## Drop reason
- 2026-08-29: duplicate: COV001 strata-core cluster already covered by T-3343 (COV/TICK/REL/REG/REF clusters), filed by owner same day (absorbed by T-3343)
