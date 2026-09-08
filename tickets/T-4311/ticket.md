---
id: T-4311
title: T-4305's declared scope misses .github/workflows/ci.yml that its own frob:tests
  directives cover
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets.md
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
SCOPE002 fires on T-4305 (tests/test_ci_workflow_timeout.py) because that file's own pre-existing frob:tests .github/workflows/ci.yml directives are not covered by the ticket's declared scope glob. Widening via 'frob ticket scope T-4305 --add .github/workflows/ci.yml' is blocked by T-4269's live cross-worktree lease on that same path (ScopeLeaseConflict). This is pre-existing (reproduces even with T-4305's own diff reverted) and unrelated to T-4305's actual fix (rebinding a stranded WIRE001 waiver). Add the glob once T-4269 lands, or find another way to satisfy SCOPE002 for read-only frob:tests references into a file this ticket does not modify.