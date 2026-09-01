---
id: T-3650
title: 'refactor split/move: self-import verify failure once destination already defines
  a bare-name helper the moved symbol references'
state: in-progress
kind: bug
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
- src/frob/refactor/**
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
Found while working T-3594 (split tests/unit/test_coordinator_scripts.py into tests/unit/coordinator_suite/*.py, reusing T-3586/T-3593's recipe). Companion gap to T-3645/T-3646 (filed during T-3593's sibling split).

frob refactor split and frob refactor move both refuse with a self-import verify failure once the DESTINATION module already defines a bare-name module-level helper (moved there in a prior split/move step) that the symbol currently being moved references. The tool re-adds 'from <dest-module> import <helper>' INTO <dest-module> itself, rather than recognizing the helper is already a local name there and needs no import at all.

Repro (T-3594):
  uv run frob refactor move tests.unit.test_coordinator_scripts:_run_git tests.unit.coordinator_suite.test_fleet_worktrees:_run_git --skip-check-delta
  # succeeds -- _run_git now lives in test_fleet_worktrees.py
  uv run frob refactor split tests.unit.test_coordinator_scripts --symbols TestResolveRepoRoot --into tests.unit.coordinator_suite.test_fleet_worktrees --skip-check-delta
  # TestResolveRepoRoot's own _init_repo method (or a module-level helper it
  # calls) references _run_git as a bare name; split correctly resolves that
  # _run_git already lives in the SAME destination module, then still emits
  # 'from tests.unit.coordinator_suite.test_fleet_worktrees import ...' inside
  # test_fleet_worktrees.py -- refused by the tool's own no_self_import check:
  #   self-import 'from tests.unit.coordinator_suite.test_fleet_worktrees
  #   import ...' -- this file importing from its own module

Measured impact this session: hit this for every helper that got moved ahead of its first-using class (_diag, _run_git, _init_bare_repo, _write_proc_locks across T-3594's check_summary/fleet_worktrees/fleet_land families), and again for T-3593's shared conftest.py-relocated helpers when the FIRST class landing in a fresh destination module already carried the import. Worked around by hand: cut the exact class block via a small python script (never hand-retyped) instead of using split/move for those specific symbols. 9 classes needed this workaround in T-3594 alone.

Suggested fix: when computing carry-forward imports for a moved symbol, check whether the referenced name is ALREADY DEFINED (as a module-level def/class/assignment) in the DESTINATION module before emitting an import statement for it -- skip the import entirely in that case, the same way the tool already skips imports for names defined in the destination via other means.