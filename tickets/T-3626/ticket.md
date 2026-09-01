---
id: T-3626
title: 'LARGE001: split .claude/hooks/root-write-guard.py (834 lines)'
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
- .claude/hooks/root-write-guard.py
- tests/**/*root_write_guard*
- tests/**/*root-write-guard*
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
LARGE001: .claude/hooks/root-write-guard.py is 834 lines, over the
800-line LARGE001 threshold. Split the hook entry point from its
importable helpers -- preserve the hook's entry contract exactly (same
CLI invocation shape, same stdout/exit-code behavior other tooling
depends on). Edit the REPO copy (not the materialized
~/.claude/hooks/ copy). After splitting, run
`uv run frob claude sync --check` and run the hook suite 3x to check
for flakiness introduced by the split.

Scope: .claude/hooks/root-write-guard.py + its test file(s).

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.
