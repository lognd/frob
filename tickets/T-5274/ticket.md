---
id: T-5274
title: Wire DSTACK001 into gates dispatch, TIER_A_HANDLERS, and frob.toml threshold
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/gates/__init__.py
- src/frob/gates/_fix_engine.py
- frob.toml
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: closed-set TIER_A_HANDLERS coverage test must list DSTACK001 (brief-mandated)
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/gates_suite/test_fix_engine.py::TestDstack001Wiring::test_dstack001_fires_through_run_gates_and_fix_is_idempotent
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5274
branch: t-5274
---
found while working T-4713: frob.gates._directive_stack.stack_lint_violations (DSTACK001) and frob.gates._fix_engine_text.fix_dstack001_merge exist and are tested, but are not yet called from anywhere -- run_gates in gates/__init__.py never collects stack_lint_violations into the violation set, and TIER_A_HANDLERS in _fix_engine.py never registers fix_dstack001_merge. Both files were outside T-4713's declared scope. Also: the stack threshold (default 4) is a Python-level parameter only -- frob.toml wiring was blocked by a lease collision with the concurrently in-progress T-4663 (scope 'frob.toml'); this ticket should add a [tool.frob] (or similar) config key and thread it through.