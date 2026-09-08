---
id: T-4201
title: 'land: make ticket.md mirror commits merge-safe so accept/scope transitions
  don''t conflict with the worktree''s own file'
state: in-progress
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
Consumer F-331 (T-4135). Three lands in a row needed git merge main before landing, and every merge conflicted on exactly one file: tickets/T-xxxx/ticket.md, because frob mirrors accept/scope transitions onto main as separate commits while the worktree's own copy moves on to close. Either mirror the whole ticket file byte-for-byte, or give it a merge driver that takes the worktree side. Fixture-testable: YES, consumer-blocking now.