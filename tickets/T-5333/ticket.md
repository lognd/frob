---
id: T-5333
title: squawk migration-safety adapter
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5334
parent: T-5148
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/sql/_squawk_adapter.py
- src/frob/doctor.py
- tests/fixtures/sql/squawk/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/sql/**
  reason: avoid overlapping T-5339's tests/fixtures/sql/explain/** and other sibling
    fixture subdirs
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/sql/squawk/**
  reason: avoid overlapping T-5339's tests/fixtures/sql/explain/** and other sibling
    fixture subdirs
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5333
branch: t-5333
---
_RELEVANT_TOOLS entry for squawk (T-5139 pattern, OPTIONAL_FOR_GATE -- migrations are a narrower relevance than the whole SQL family), relevant_when = a migrations directory exists. Spawn+parse squawk's JSON output into frob Violations: NOT-NULL-without-default, index-without-CONCURRENTLY, lock-taking rewrites. Fixture: a migration file with each planted anti-pattern.