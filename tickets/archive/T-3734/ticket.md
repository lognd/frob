---
id: T-3734
title: fix self-gate PERF008/coupling findings in reconcile.py from T-3731
state: done
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reconcile.py
- src/frob/tickets/_unlanded.py
- tests/test_ticket_reconcile.py
- src/frob/tickets/_unlanded_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: add doc target and evidence test file closure per scope-closure warnings
    on ticket new
  actor: logan
  at: '2026-09-03'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: add doc target and evidence test file closure per scope-closure warnings
    on ticket new
  actor: logan
  at: '2026-09-03'
- op: remove
  glob: docs/modules/tickets-lifecycle.md
  reason: 'revert: doc file balloons scope via pre-existing anchors unrelated to this
    fix; not touching docs'
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/tickets/_unlanded_cache.py
  reason: 'LARGE001 fix: extract T-3567 cache-write helper into its own module to
    shrink _unlanded.py back under the 800-line threshold (coordinator directive)'
  actor: logan
  at: '2026-09-03'
body_changes:
- mode: append
  reason: add frob:no-behavior-change per BUG002 land guard -- this ticket is a pure
    structural/self-gate fix, not a behavior fix
  actor: logan
  at: '2026-09-03'
  old_length: 690
  new_length: 1140
evidence:
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_doable_summary_cache
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_cache_even_on_a_dry_run
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_skips_the_cache_write_when_frob_dir_is_not_gitignored
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 33729699769 ubuntu/mac self-gate: T-3731 author only ran --only coverage --only tickets, missing perf/arch gates. New error-severity findings on reconcile area: PERF008 at src/frob/tickets/_reconcile.py:101 (Path(...) constructed inside loop with loop-invariant args), and high-coupling on reconcile.py (imports 9 local modules, threshold 8). Fix: hoist the Path prefix computation out of the git-worktree-list parse loop; reduce coupling by moving the T-3567 unlanded-summary-cache helper (_maybe_save_unlanded_summary_cache / _frob_dir_is_gitignored) into _unlanded.py, which reconcile.py already imports, dropping the direct frob.app.ticket_runner._query import from reconcile.py.

frob:no-behavior-change reason="T-3734 is a self-gate remediation: hoisting a loop-invariant Path() computation, moving two helper functions to a new module for a re-export, and adding reasoned frob:waive directives. No production behavior changes -- the reconcile/unlanded-cache logic itself, its inputs, and its outputs are unchanged; only file/module structure and import wiring moved. T-3731 own 20s scan budget behavior is preserved verbatim."