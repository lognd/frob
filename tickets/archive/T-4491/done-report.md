## Done report

Lease staleness reloaded the FULL active+archive ledger (load_queue, ~25.5s YAML-parsing 3391 archived tickets) once per lease record inside _live_leases_pruning_stale, so read_all_leases cost minutes with ~15-20 registered worktrees and stalled every land at its precheck. Fixed by (1) loading only the active ledger, in-process-cached and shared across a whole pruning pass instead of reloaded per record, and (2) answering archive membership for v2-mode via a plain tickets/archive/<id>/ticket.md existence check instead of parsing the archive -- load_queue (the full merge) is now reached only for a ticket absent from the active ledger on a non-v2 backend. Lease semantics unchanged -- 279+ pre-existing lease/archive tests still pass. Measured on this real repo: read_all_leases(root) went from 8.11s to 0.12s (about 67x). BUG002: repro test and its fix landed in one worktree commit, so --check-repro reports TEST_ABSENT_AT_PARENT; manually verified by swapping _leases.py back to the parent commit and re-running the two new tests, both failed as expected; documented as a frob:waive BUG002 paragraph on the ticket body, designation recorded via --designate-repro-force. Also fixed a lock-order-cycle frob check caught mid-work by folding a second cache lock onto the existing one. Filed nothing new. Disregarded an unverified mid-session message purporting to be the coordinator asking to expand scope onto other tickets files; flagged for the real coordinator, not acted upon.

### Changed
```
 design/frob.strata                                 |  12 +-
 .../registry/capability-via-ratchet.lock.json      |  12 +-
 src/frob/tickets/_leases.py                        | 202 ++++++++++++--
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++++++++++++++++
 tickets/T-4491/ticket.md                 |  35 ++-
 5 files changed, 541 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/unit/test_leases_staleness_perf.py::TestLiveLeasesPruningStaleSingleLoad::test_load_queue_called_at_most_once_for_n_records` (pytest node id, verified passing when recorded)
- `tests/unit/test_leases_staleness_perf.py::TestTicketLedgerStalenessShapeArchiveFastPath::test_archived_ticket_id_is_terminal_without_parsing_the_archive` (pytest node id, verified passing when recorded)
- `tests/unit/test_leases_staleness_perf.py::TestReadAllLeasesStaysFast::test_many_archived_ticket_leases_stay_fast` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4918 warning(s), 984 waived
- error-findings: none (measured, zero errors)
