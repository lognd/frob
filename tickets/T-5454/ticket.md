---
id: T-5454
title: Fix a11y_findings signature to match T-5323 per-file gate contract
state: in-progress
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_a11y_statement.py
- tests/unit/test_webapp_a11y_statement.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_webapp_a11y_statement.py
  reason: test file covering rewritten per-file a11y_findings + e2e a11y_gate integration
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5454
branch: t-5454
---
T-5323's a11y_gate() calls every discovered hook as a11y_findings(ctx: A11yFileContext, frameworks) once per parsed file; src/frob/webapp/_a11y_statement.py still implements a11y_findings(root: Path, frameworks), so frob.gates._a11y_gate.a11y_gate() crashes with TypeError on any repo with a detected framework. Rework to the per-file contract (memoized repo-level statement detection), keep A11Y107-114 semantics and fixtures, add an end-to-end test exercising a11y_gate() over a throwaway repo.