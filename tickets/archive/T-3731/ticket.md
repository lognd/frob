---
id: T-3731
title: reconcile hangs scanning all local branches (unbounded unlanded-work scan)
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
- src/frob/tickets/_unlanded.py
- src/frob/tickets/_reconcile.py
- tests/unit/test_unlanded_branch_work.py
- tests/test_ticket_reconcile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_budget_of_zero_scans_no_branches
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_a_generous_budget_still_scans_everything
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_the_default_budget_is_a_small_finite_number
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_reconcile_does_not_hang_with_many_branches
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_unparseable_override_falls_back_to_default_not_unbounded
  new_node: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_the_default_budget_is_a_small_finite_number
  reason: 'T-3731: dropped env-var override; replaced with a module-level constant
    tests monkeypatch directly, so the two env-var tests collapsed into one default-value
    assertion'
  actor: logan
  at: '2026-09-03'
- old_node: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_no_override_uses_the_finite_default
  new_node: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkScanBudget::test_the_default_budget_is_a_small_finite_number
  reason: 'T-3731: dedupe -- same collapsed env-var-removal rebind as the other stale
    env-var test id'
  actor: logan
  at: '2026-09-03'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 33721091819 (ubuntu+mac): uv run frob ticket reconcile --apply hung
36+ minutes and hit the 60-minute job timeout, cancelling both legs.
Self-gate finished 0 errors at 06:22, reconcile started at 06:22, job
killed at 06:58.

Root cause: frob.tickets._reconcile.reconcile unconditionally calls
_unlanded_branch_work(root) (T-1934/T-1948), which iterates EVERY local
branch (_local_branch_names) with no cap. This repo currently has 1578
local branches (measured 2026-09-03; T-2125's own docstring already
recorded 644 as a hotspot needing the git-grep batching fix it made).
Per branch this runs a three-dot diff, a ls-tree, a git-grep, and
potentially one git show plus frob.lang.parse_file per changed
non-tickets file (T-1948's directive-anchor signal). With 1578 branches
the aggregate cost is minutes-to-tens-of-minutes, matching the observed
CI hang.

Related: T-3710 documents a DIFFERENT symptom of the same archive/active
ledger churn (T-0450 present in both stores causes DuplicateId on
write) -- not the same bug as this scan-cost hang, but check whether
bounding/skipping desynced ids here also touches that path.

Fix: bound _unlanded_branch_work's branch scan (cap branch count and/or
add a time budget with early exit and warning log) so
frob ticket reconcile --apply completes in seconds on this repo. Add a
regression test proving the scan stays bounded with a large number of
local branches.