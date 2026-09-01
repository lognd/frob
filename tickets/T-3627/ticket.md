---
id: T-3627
title: 'LARGE001: split src/frob/arch/_mayraise.py (878 lines)'
state: queued
kind: feature
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
- tests/**/*mayraise*
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
LARGE001: src/frob/arch/_mayraise.py is 878 lines, over the 800-line
threshold. Split along the rule/table boundary already present in the
file (the rule-evaluation logic vs. the rule table/data). Keep
behavior identical.

Scope: src/frob/arch/_mayraise.py + its test file.

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.
