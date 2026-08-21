---
id: T-1945
title: Bulk-reformat the 77 ruff-format + 265 frob-fmt drifted files (deferred from
  T-1928)
state: queued
kind: feature
origin: human
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- '''tests/conftest.py'''
- '''tests/test_app.py'''
- '''tests/test_capability_registry.py'''
- '''tests/test_check_runner.py'''
- '''tests/test_coverage_wait_shared.py'''
- '''tests/test_doc012_promotion.py'''
- '''tests/test_docenum_gate.py'''
- '''tests/test_gates.py'''
- '''tests/test_gates_fix_engine.py'''
- '''tests/test_gates_suppress.py'''
- '''tests/test_graph.py'''
- '''tests/test_graph_imports.py'''
- '''tests/test_hook_diagnosis_nudge.py'''
- '''tests/test_land_verify_claims_outcome.py'''
- '''tests/test_lang_conformance_gate.py'''
- '''tests/test_pii_structural_gate.py'''
- '''tests/test_refactor.py'''
- '''tests/test_release.py'''
- '''tests/test_scaffold_worktree_lease_hook.py'''
- '''tests/test_serve_tools_daemon_bypass.py'''
- '''tests/test_telemetry.py'''
- '''tests/test_testing.py'''
- '''tests/test_tick012_gate.py'''
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: '**/*.py'
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: tests/unit/strata/litmus/**
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/conftest.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_app.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_capability_registry.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_check_runner.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_coverage_wait_shared.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_doc012_promotion.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_docenum_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates_fix_engine.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates_suppress.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_graph.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_graph_imports.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_hook_diagnosis_nudge.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_land_verify_claims_outcome.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_lang_conformance_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_pii_structural_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_refactor.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_release.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_scaffold_worktree_lease_hook.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_serve_tools_daemon_bypass.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_telemetry.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_testing.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_tick012_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1928 measured, on a clean main tree (2026-08-10), three genuinely
different things all named "fmt" that answer different questions:

- `frob check --only fmt` (gate:FMT / FMT001): diff-scoped by
  construction (`fmt_gate`, src/frob/gates/_todo_fmt.py, only inspects
  `frob:` directive-comment lines the CURRENT DIFF touches). On a clean
  tree this is correctly 0 errors in ~0s -- it did no work because there
  was no diff to examine, not because the repo is formatted.
- `ruff format --check .` (the "ruff-format" tool inside `frob check`'s
  unscoped lint stage, src/frob/check/_python.py::_ruff_format_result):
  77 .py files with real ruff code-style drift, repo-wide.
- `frob fmt --check` (standalone CLI, src/frob/app/fmt_runner.py): 265
  files (215 .py + 49 .strata) needing `frob:` directive-comment
  line-wrap canonicalization, repo-wide -- a DIFFERENT concern from ruff
  code style. Overlap between the two .py lists is only 7 files out of
  215/77 -- these are almost entirely disjoint drift populations, not
  the same drift measured two ways.

T-1928's explicit non-goal was "do not open with a mass reformat" (a
265+77-file reformat commit is unreviewable and collides with every live
worktree). Per T-1928's acceptance [4], recording that decision here
explicitly rather than leaving it implicit in a passing gate:

DECISION (2026-08-10): the 77-file ruff-format drift and the 265-file
frob-fmt drift are ACCEPTED, KNOWN, UNACTIONED debt for now. Neither is
silently "fixed" by T-1928 (which only adds disclosure, per its own
non-goal). This ticket tracks the actual bulk-reformat work, to be
sequenced separately, deliberately, when the live `.claude/worktrees/*`
count is low enough that a large mechanical diff will not collide with
concurrent agents' in-flight work. Suggested shape when picked up: two
separate commits (ruff-format's 77 files; frob-fmt's 265 files), not one
combined diff, since they are different tools fixing different concerns
and either could regress independently.
