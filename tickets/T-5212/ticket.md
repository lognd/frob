---
id: T-5212
title: Wire _rapid_caller_dependents to public_caller_dependent_files
state: done
kind: feature
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_check_scoped_files.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_scoped_files.py
  reason: T-5212 needs a positive-control test proving the public-caller wiring end
    to end; test file was not in the original ticket scope
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_public_symbol_caller_is_included
- tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_three_callers_of_a_changed_function_are_included
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5212
branch: t-5212
---
found while working T-4560: build_call_graph gained an opt-in include_public_callees flag and frob.graph.affects gained public_caller_dependent_files, but _land_cmd.py's _rapid_caller_dependents (out of T-4560's declared/implicit scope) still only calls the private-only caller_dependent_files. Wire it to also call public_caller_dependent_files (or replace the call) so the rapid land's --files dependents scope actually picks up callers of a changed PUBLIC symbol end to end.