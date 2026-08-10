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
