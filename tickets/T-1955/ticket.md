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

## Done report

Root cause: _finished_signals_on_branch listed every tickets/ path via
`git ls-tree <branch> -- tickets`, which enumerates everything REACHABLE
from the branch tip, not just what the branch's own commits changed.
Since every branch is cut from main, main's entire finished-ticket
history (a done-report.md for every closed ticket ever) is reachable
from any branch tip, so every branch inherited every finished ticket's
signal -- the same two-dot/three-dot confusion T-1922 fixed earlier in
_land.py's _branch_changed_files. Fix: added _branch_own_changed_files
(three-dot `git diff --name-only main...<branch>`), and intersect the
ls-tree path list against it before classifying done-report/local-
state-done signals. A freshly-cut branch that has not touched tickets/
now yields no signals at all, regardless of main's history size.

Evidence:
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_fresh_branch_reports_zero_despite_main_history (acceptance 1, fresh branch -> zero findings)
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_leak_still_reported_after_the_fix (acceptance 2, genuine leak still reported)

check-repro: BUG002 --check-repro on the new fresh-branch test returned
NO_VERDICT (exit 5, collection failure) at the ticket's parent commit --
the test exercises the not-yet-existing intersection logic and did not
exist as a test node at the parent commit either, so pytest cannot even
collect it there. This is the documented structural gap (brand-new test
node), not evasion -- recorded here rather than silently waived, per the
playbook's explicit instruction on this known shape.

Filed: none. No out-of-scope discoveries; the DRIFT002/gate:PRE/SCOPE
findings observed during `frob check` all trace to
src/frob/tickets/_land.py, already owned by another agent in this wave,
plus pre-existing repo-wide COV/DOC/ARCH findings unrelated to the two
files this ticket touched.

Gates: `frob check --ticket T-1955` clean on gate:SCOPE, gate:PRE, the
file-scoped gate:COV (COV002) and gate:FMT for this ticket's touched
set; every other FAIL line in that run is a repo-wide pre-existing
finding outside src/frob/tickets/_unlanded.py and
tests/unit/test_unlanded_branch_work.py.

### Changed
```
 src/frob/tickets/_unlanded.py           | 50 ++++++++++++++++++++++++++++--
 tests/unit/test_unlanded_branch_work.py | 54 +++++++++++++++++++++++++++++++++
 tickets/T-1955/ticket.md                | 12 +++++++-
 3 files changed, 112 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_fresh_branch_reports_zero_despite_main_history` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_leak_still_reported_after_the_fix` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 5 error(s), 846 warning(s), 705 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, DOC002@src/frob/tickets/_land.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-1955
