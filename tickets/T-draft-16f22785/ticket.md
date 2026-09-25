---
id: T-draft-16f22785
title: 'land --drain: re-exec between lands when frob''s own source changed'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket land --drain` runs every queued entry in ONE python
process. With 40+ entries queued it never exits, so engine fixes that
LAND during the drain (today: T-5518, T-5522, T-5785, T-draft-42b1e188)
do not take effect until someone kills and restarts it, and a kill mid-
land is unsafe. Fix: at the top of each drain iteration, between lands,
compare the mtime/tree hash of frob's own installed source (the
`frob` package directory plus the native extensions) against the value
captured at process start; on change, log it and `os.execv` the same
argv so the next land runs the new code (leases, queue file and
land.lock are all durable, so a between-lands re-exec loses nothing).
Positive control: touch a frob source file during a drain of two
entries; the second entry's land log must show the new process pid.
Tiered-safety: automatic, logged.
