---
id: T-1955
title: T-1934's unlanded detector reports 216 false positives (4 tickets x 77 branches),
  including branches cut minutes ago
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: acceptance tests for the criterion fix live in this file
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_fresh_branch_reports_zero_despite_main_history
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_leak_still_reported_after_the_fix
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REGRESSION from T-1934's land (a3c92dfc0c04). The unlanded-work detector
is correct in principle but its criterion matches something present on
main itself, so it reports a cross-product of tickets x branches.

MEASURED, immediately post-land, on main:

  `uv run frob ticket reconcile` prints:
    "216 branch(es) carry unlanded ticket work"

  216 entries = 4 DISTINCT tickets x 77 branches:
    T-1238  x77   (appears on EVERY branch)
    T-1778  x47
    T-1831  x46
    T-1820  x46

PROOF THESE ARE FALSE POSITIVES, not a real backlog: the flagged set
includes branches created MINUTES BEFORE the measurement as part of the
current dispatch wave -- `floor-zero`, `strata-dedup`, `rule-registry`,
`config-sync`, `dead-branch`. Those branches were cut from main and
contain only their own fresh work; they cannot carry "finished but
unlanded" work for T-1238, an unrelated queued CLI-regrouping epic. A
signal that fires on a branch created five minutes ago is matching
something that lives on main, not on the branch.

WHY IT IS URGENT DESPITE HARMING NOTHING: `frob ticket reconcile` is a
high-traffic command, and this dumps a 216-item single-line wall into its
output. The predictable outcome is that operators and agents learn to
skip that section -- which destroys exactly the signal T-1934 was built
to provide. A detector that cries wolf 216 times is worse than no
detector, because the real leak (there IS at least one: T-1691, tracked
as T-1948) is now buried in noise.

DO NOT FIX IT THIS WAY: do not suppress the section, cap it at top-N, or
silence these four ticket ids specifically. That hides the false
positives without fixing the criterion, and a capped list silently drops
real leaks -- the same "no silent caps" failure this repo has hit before.
Fix the criterion so a freshly-cut branch reports zero.

DIAGNOSTIC STARTING POINT: whatever the criterion is, it must be
evaluated against what the BRANCH's own commits changed (three-dot
`main...branch` semantics), not against content reachable from the
branch. The identical two-dot/three-dot confusion was the root cause of
T-1922, fixed hours earlier in this same subsystem -- check for the same
mistake here first.

ACCEPTANCE: first test must FAIL before the fix -- cut a fresh branch
from main, run the detector, assert it reports ZERO unlanded tickets for
that branch. Then assert a genuine leak (a branch with a done-report and
a non-terminal state on main) is still reported. Then re-run
`frob ticket reconcile` on this repo and report the new count with its
per-ticket breakdown.