---
id: T-4413
title: 'Rapid profile: scoped gate sweep replaces unscoped pre-land baseline check'
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4411
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/verify
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a rapid land WHEN the synchronous pre-land check runs THEN it replaces
    the T-1463 unscoped full in-process frob check with a scoped gate sweep over diff-touched
    files plus their direct dependents (via frob affects / callgraph)
  evidence: []
- text: GIVEN a rapid land WHEN the scoped sweep runs THEN touched-set tests and bound
    evidence collection are preserved unchanged from today
  evidence: []
- text: GIVEN a rapid land of a one-file change on this repo WHEN measured THEN the
    synchronous phase completes in under 3 minutes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11): CI is the single source of full-suite/full-gate truth; land must prove only the diff. Currently rapid still runs the T-1463 baseline-capture thread -- a full in-process frob check -- feeding the post-land sweep (src/frob/app/ticket_runner/_land_cmd.py around line 5570, citing T-1575's deferred baseline-thread-free rapid path). With ~4200 tickets/~1400 files this takes 25-45 minutes per land (T-4408: 50+ min). Replace the unscoped baseline with a scoped sweep.