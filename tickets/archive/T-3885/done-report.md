## Done report

Changed:
src/frob/tickets/_leases.py::_proc_ppid_linux
src/frob/tickets/_leases.py::_proc_ppid_darwin
src/frob/tickets/_leases.py::_proc_ppid
src/frob/tickets/_leases.py::_process_ancestor_pids
src/frob/tickets/_leases.py::_scan_for_live_land_process
tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_a_land_targeting_a_different_repo_does_not_block_this_one
tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_a_land_does_not_block_on_its_own_descendant

Evidence:
tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_a_land_does_not_block_on_its_own_descendant

Filed: none

Gates: frob check --ticket T-3885 clean of scope-relevant findings; the
2 remaining COV003/COV007 findings are pre-existing repo-wide gate
results unrelated to this diff (T-4346, src/frob/tickets/
_mutation_evidence.py -- neither touched here).

Investigation finding worth recording: defect (a) from the ticket body
(cross-repo false-positive block) was MEASURED as already fixed in this
repo's current state before I touched anything -- `_scan_for_live_land_
process` already filters by exact cwd equality via `_live_pids_with_cwd`,
and a real two-process test (test_a_land_targeting_a_different_repo_
does_not_block_this_one) passes even against the pre-fix parent commit
(confirmatory-only, not bound as BUG002 evidence, but kept in the diff
as a regression lock and cited here). Defect (b), the self-deadlock
(F-098), was NOT fixed: _scan_for_live_land_process's self-exclusion
only skipped one exact exclude_pid, so a land's own multi-pid process
tree (bash wrapper, timeout, uv run, python) could match itself. Fixed
via a proper ancestor-chain walk (_process_ancestor_pids), verified
FAILED_AT_PARENT/PASSED_AT_FIX via a real 3-process test (grandparent ->
parent -> child, matching the measured 3-4-pid-deep shape).

scripts/fleet_status.py's OWN separate implementation
(land_process_rows/land_invocations, machine-wide ps scan with NO cwd
or repo filter at all) is a genuinely different, unscoped predicate the
original ticket also asked to fix ("CHECK fleet_status.py TOO... if they
duplicate the logic, that duplication is itself worth removing") -- left
untouched per this series' "tight scope on the lock module and its
test" instruction. This is real remaining exposure (fleet_status's
LANDS IN FLIGHT can still misreport a foreign repo's land) and should be
tracked as a fast follow.

### Changed
```
 src/frob/tickets/_leases.py | 126 +++++++++++++++++++++++++++++++++++++++++++-
 tests/test_ticket_leases.py | 112 +++++++++++++++++++++++++++++++++++++++
 tickets/T-3885/ticket.md    |  29 +++++++++-
 3 files changed, 264 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_a_land_does_not_block_on_its_own_descendant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4793 warning(s), 957 waived
- error-findings: COV003@tickets/T-4364/ticket.md, COV007@src/frob/tickets/_mutation_evidence.py
