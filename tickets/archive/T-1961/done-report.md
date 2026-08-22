## Done report

Changed:
src/frob/tickets/_leases.py::refuse_if_land_in_progress (now waits, bounded)
src/frob/tickets/_leases.py::_probe_land_once (new, extracted for ARCH001)
src/frob/tickets/_leases.py::_land_flock_probe (added quiet= param)
src/frob/tickets/_leases.py::_refuse_for_held_land_lock (added quiet= param)

Evidence:
tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees
tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly
Repro confirmed both via frob's own --check-repro-force (same known
PYTHONPATH bug as T-2005) and directly via git show on the parent
commit's source (old signature has no wait_timeout_s kwarg).

Filed: none new (T-2005 already covers the check-repro PYTHONPATH bug)

Gates: full tests/test_ticket_leases.py suite green except one
pre-existing, unrelated failure (TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for,
already broken at main tip 392fb9cd5 before this ticket -- a prior
land added an "anchor" verb to the dispatch table without updating
this enumeration test; confirmed via git grep on main, not introduced
here). ARCH001/ty clean on src/frob/tickets/_leases.py.

Direction (a) implemented per the ticket's own preferred order: the
lock check itself and T-1619's belt-and-braces process scan are
unchanged; callers are not made responsible for retrying.

### Changed
```
 src/frob/tickets/_leases.py | 177 ++++++++++++++++++++++++++++----------------
 tests/test_ticket_leases.py | 115 +++++++++++++++++++++++++++-
 tickets/T-1961/ticket.md    |   7 +-
 3 files changed, 228 insertions(+), 71 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1961
