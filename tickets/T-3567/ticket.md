---
id: T-3567
title: T-3522's reconcile cache write leaves .frob/unlanded-summary-cache.json untracked,
  breaking T-1936 leaves-clean contract
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reconcile.py
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
run 33370059331: tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileAutoCommit::test_apply_leaves_the_ledger_clean and TestReconcileRemoveOrphansAutoCommit::test_apply_with_remove_orphans_still_leaves_ledger_clean both fail (linux, fully reproducible, not flaky) asserting git status is clean after reconcile(apply=True) but see '?? .frob/unlanded-summary-cache.json'. T-3522 wired _save_unlanded_summary_cache into reconcile() unconditionally; in the test fixture repo (and any consumer repo without frob's own top-level .gitignore) .frob/ is not gitignored, so this new write is an untracked file T-1936's leaves-the-ledger-clean contract did not previously have to account for. Fix: reconcile should ensure .frob/ is gitignored the way frob's other .frob/ writers do (find and reuse the existing ensure-ignored helper if one exists), or route the cache write through whatever mechanism the other .frob state files use that keeps these tests green -- not a change to the tests' own assertion.