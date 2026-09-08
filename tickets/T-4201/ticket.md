---
id: T-4201
title: 'land: make ticket.md mirror commits merge-safe so accept/scope transitions
  don''t conflict with the worktree''s own file'
state: done
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner
- tests/test_ticket_merge_driver.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_merge_driver.py
  reason: T-4201's fix and its own repro test live in this file; the fix itself is
    in the already-declared src/frob/app/ticket_runner scope
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_single_ticket_file_unchanged_mirror_side_does_not_resurrect_stale_evidence
designated_repro_test: tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_single_ticket_file_unchanged_mirror_side_does_not_resurrect_stale_evidence
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-331 (T-4135). Three lands in a row needed git merge main before landing, and every merge conflicted on exactly one file: tickets/T-xxxx/ticket.md, because frob mirrors accept/scope transitions onto main as separate commits while the worktree's own copy moves on to close. Either mirror the whole ticket file byte-for-byte, or give it a merge driver that takes the worktree side. Fixture-testable: YES, consumer-blocking now.