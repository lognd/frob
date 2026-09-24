---
id: T-5339
title: EXPLAIN-obligation proof gate for waived SQL performance findings
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5335
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
- src/frob/gates/_sql_explain_obligation.py
- tests/fixtures/sql/explain/**
- tests/unit/test_sql_explain_obligation.py
- docs/modules/gates.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/sql/**
  reason: use per-ticket fixture subdir tests/fixtures/sql/explain/** to avoid overlapping
    T-5333's fixtures, per coordinator instruction
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/sql/explain/**
  reason: use per-ticket fixture subdir tests/fixtures/sql/explain/** to avoid overlapping
    T-5333's fixtures, per coordinator instruction
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_sql_explain_obligation.py
  reason: 'unit test for the new gate function (BRIEF item: prove positive control
    with a real test that calls the gate function)'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/gates.md
  reason: T-2114 frob:doc edge for sql_explain_obligation_gate + register SQLEXPLAIN001
    in _KNOWN_GATE_RULES
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_waive.py
  reason: T-2114 frob:doc edge for sql_explain_obligation_gate + register SQLEXPLAIN001
    in _KNOWN_GATE_RULES
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5339
branch: t-5339
---
A query flagged by 5148-2's performance rules carries a frob:tests-style obligation requiring an attached EXPLAIN ANALYZE artifact before a frob:waive on that finding is accepted -- reuse the closest existing 'proof required before waiver' precedent in frob.gates (grep for frob:invariant's binding mechanism) rather than inventing a new obligation shape. Fixture: a waiver attempt with and without the attached EXPLAIN artifact.