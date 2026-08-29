---
id: T-3397
title: Reduce ARCH103 decision-point count in _land_cmd._assert_touched_files_lint_clean_pre_land
state: queued
kind: bug
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
- src/frob/app/ticket_runner/_land_cmd.py
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
ARCH103 fires on _assert_touched_files_lint_clean_pre_land (6 decision points, I/O + string-formatting). A safe fix needs a consolidating split (per T-3311's lesson: moving code around does not reduce the caller's own branch count unless the split owns ALL the branching) rather than a blind extraction, so it is deferred as tracked follow-up work rather than attempted as a drive-by in a mixed-gate cleanup slice.