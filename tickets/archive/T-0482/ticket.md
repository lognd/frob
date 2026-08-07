---
id: T-0482
title: 'WALK-lint migration: check/_python.py rglob sites'
state: dropped
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_python.py
- tests/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_check.py
  reason: T-draft-b4a0b4be check work maps to tests/test_check.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
- tests/test_walk_lint_gate.py::TestSelfMatchExclusion::test_own_files_not_scanned
- tests/test_walk_migration.py::test_arch_does_not_walk_nested_worktree
designated_repro_test: null
threat: null
component: null
---
found while working T-0471: WALK001's gate flags 3 raw traversal sites in src/frob/check/_python.py (_build_import_graph:131 scan_root.rglob('*.py') with a hand-maintained skip set duplicating frob.excludes.BUILTIN_SKIP_DIRS; _has_bind_markers:691 scan.rglob('*.py'); _run_exports:783 scan.rglob('__init__.py')) that T-0471's own declared scope (src/frob/excludes.py, src/frob/gates/, src/frob/arch/, src/frob/xref/, src/frob/vet/, docs/, tests/**) did not cover, even though the ticket body named check/_python.py as a migration target. Migrate all three to frob.excludes.iter_files (suffix='.py' / suffix=None + name filter), same shape as the arch/xref/vet migrations T-0471 landed. A prototype migration was drafted and reverted in T-0471's worktree for SCOPE001; the diff shape is straightforward (see T-0471 Done report).

Dropped (2026-07-21): work already landed upstream in 428c753 (coordinator WALK001 sweep) before this ticket was picked up; verification evidence recorded below, nothing left to implement.