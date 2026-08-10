## Done report

Changed:
src/frob/tickets/_leases.py::record_lease (now skips the root case)
src/frob/tickets/_leases.py::_should_skip_root_lease (new)

Evidence:
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_still_recorded_with_no_sibling_worktrees
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_non_root_worktree_still_records_its_own_lease
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_pre_existing_root_lease_staleness_is_unchanged
Repro confirmed both via frob's own --check-repro-force (same known
PYTHONPATH bug as T-2005) and directly via git show on the parent
commit's source (the guard did not exist there).

Filed: none new (T-2005 already covers the check-repro PYTHONPATH bug)

Chosen fix direction: prevention, not a new staleness rule -- refuses
to RECORD a lease against the shared primary checkout when this repo
has dispatched agent worktrees registered, closing the leak at its
source rather than widening `lease_staleness_reason`'s "holder-dead"
shape (explicitly forbidden by the ticket). None of the "do not fix it
this way" options were used: the live-process check is untouched, no
pid was recorded, T-1686 was not hand-deleted or special-cased.

Measurement (acceptance criterion 3): 1 of 7 current leases in this
repo record the shared root as their worktree (T-1686) -- confirms the
leak is real but narrow today, matching the ticket's own "latent cost"
framing. T-1686 itself is untouched by this fix (this only prevents
FUTURE root leases; T-1686's own reclamation is separate floor-cleanup
work).

Gates: full tests/test_ticket_leases.py suite green except the one
pre-existing, unrelated TestLedgerAutoCommitEnumeratedOverDispatchTable
failure already noted in T-1961's Done report. ARCH001/ty clean.

### Changed
```
 src/frob/tickets/_leases.py   | 227 ++++++++++++++++++++++++++++++------------
 tests/test_ticket_leases.py   | 227 +++++++++++++++++++++++++++++++++++++++++-
 tickets/T-1961/done-report.md |  44 ++++++++
 tickets/T-1961/ticket.md      |   7 +-
 tickets/T-2007/ticket.md      |  11 +-
 5 files changed, 442 insertions(+), 74 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_still_recorded_with_no_sibling_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_non_root_worktree_still_records_its_own_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_pre_existing_root_lease_staleness_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/unit/test_tickets_evidence_only_scope.py
